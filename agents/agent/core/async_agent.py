import logging
import time
from typing import Optional, AsyncIterator, List, Callable

import yaml
from langchain_core.messages import BaseMessageChunk

from agents.agent.core import exists, concat_strings, BaseDeepcoreAgent
from agents.agent.entity.inner.node_data import NodeMessage
from agents.agent.entity.inner.tool_output import ToolOutput
from agents.agent.memory.memory import MemoryObject
from agents.agent.tools.tool_executor import async_execute

logger = logging.getLogger(__name__)


class AsyncAgent(BaseDeepcoreAgent):

    def __init__(
            self,
            tools: Optional[List[Callable]] = None,
            async_tools: Optional[List[Callable]] = None,
            should_send_node: Optional[bool] = False,
            *args,
            **kwargs,
    ):
        """
        Initialize AsyncAgent with both synchronous and asynchronous tools.

        Args:
            tools: List of synchronous tool functions
            async_tools: List of asynchronous tool functions
            should_send_node: Whether to send node information to the agent. Defaults to True.
            *args: Additional positional arguments for parent class
            **kwargs: Additional keyword arguments for parent class
        """
        super().__init__(tools=None, *args, **kwargs)

        self.tools = tools or []
        self.async_tools = async_tools or []
        self._initialize_tools()
        self.should_send_node = should_send_node

    def _initialize_tools(self) -> None:
        """Initialize tool structure and function mappings."""
        all_tools = self.tools + self.async_tools

        if not (exists(all_tools) or exists(self.list_base_models) or exists(self.tool_schema)):
            return

        self.tool_struct = BaseTool(
            tools=all_tools,
            base_models=self.list_base_models,
            tool_system_prompt=self.tool_system_prompt,
        )

        if all_tools:
            logger.info(
                "Tools provided: Accessing %d tools. Ensure functions have documentation and type hints.",
                len(all_tools)
            )

            self.short_memory.add(role="system", content=self.tool_system_prompt)

            tool_dict = self.tool_struct.convert_tool_into_openai_schema()
            self.short_memory.add(role="system", content=tool_dict)

            self.function_map = {tool.__name__: tool for tool in all_tools}

    async def acompletion(
            self,
            task: Optional[str] = None,
            img: Optional[str] = None,
            is_last: Optional[bool] = False,
            *args,
            **kwargs,
    ) -> AsyncIterator[str]:
        """
        run the agent

        Args:
            task (str): The task to be performed.
            img (str): The image to be processed.
            is_last (bool): Indicates if this is the last task.

        Returns:
            Any: The output of the agent.
            (string, list, json, dict, yaml)

        Examples:
            agent(task="What is the capital of France?")
            agent(task="What is the capital of France?", img="path/to/image.jpg")
            agent(task="What is the capital of France?", img="path/to/image.jpg", is_last=True)
        """
        try:
            async for data in self.send_node_message("task understanding"): yield data

            self.check_if_no_prompt_then_autogenerate(task)

            self.agent_output.task = task

            # Add task to memory
            self.short_memory.add(role=self.user_name, content=task)

            # Plan
            if self.plan_enabled is True:
                async for data in self.send_node_message("task plan"): yield data
                self.plan(task)

            # Set the loop count
            loop_count = 0
            # Clear the short memory
            response = None
            all_responses = []

            # Query the long term memory first for the context
            if self.long_term_memory is not None:
                async for data in self.send_node_message("load past context"): yield data
                self.memory_query(task)

            # Print the user's request

            if self.autosave:
                self.save()

            while (
                    self.max_loops == "auto"
                    or loop_count < self.max_loops
            ):
                loop_count += 1
                self.loop_count_print(loop_count, self.max_loops)

                # Dynamic temperature
                if self.dynamic_temperature_enabled is True:
                    self.dynamic_temperature()

                # Task prompt
                task_prompt = (
                    self.short_memory.return_history_as_string()
                )

                # Parameters
                attempt = 0
                success = False
                should_stop = False
                while attempt < self.retry_attempts and not success:
                    try:
                        if (
                                self.long_term_memory is not None
                                and self.rag_every_loop is True
                        ):
                            logger.info(
                                "Querying RAG database for context..."
                            )
                            self.memory_query(task_prompt)

                        # Generate response using LLM
                        response_args = (
                            (task_prompt, *args)
                            if img is None
                            else (task_prompt, img, *args)
                        )
                        response = ""
                        whole_data = ""
                        logger.info(
                            f"Generating response with LLM... :{response_args}"
                        )
                        async for data in self.call_llm_in_stream(
                                *response_args, **kwargs
                        ):
                            if isinstance(data, str):
                                whole_data += data
                                response += data
                            else:
                                logger.error(
                                    f"Unexpected response format: {type(data)}"
                                )
                                raise ValueError(
                                    f"Unexpected response format: {type(data)}"
                                )

                            if (self.stopping_condition is not None
                                    and self._check_stopping_condition(response)):
                                async for data in self.send_node_message("generate response"): yield data

                            if should_stop or (
                                    self.stopping_condition is not None
                                    and self._check_stopping_condition(response)
                            ):
                                logger.info("Stopping condition met.")
                                should_stop = True
                                yield response
                                response = ""

                        response = whole_data
                        logger.info(f"Response generated successfully. {response}")

                        # Convert to a str if the response is not a str
                        response = self.llm_output_parser(response)

                        # Check if response is a dictionary and has 'choices' key
                        if (
                                isinstance(response, dict)
                                and "choices" in response
                        ):
                            response = response["choices"][0][
                                "message"
                            ]["content"]
                        elif isinstance(response, str):
                            # If response is already a string, use it as is
                            pass
                        else:
                            raise ValueError(
                                f"Unexpected response format: {type(response)}"
                            )

                        # Check and execute tools
                        if not should_stop:
                            is_finished = False
                            if self.async_tools is not None:
                                async for resp in self.async_parse_and_execute_tools(response, direct_output=True):
                                    yield ToolOutput(resp)
                                    is_finished = True
                                if is_finished:
                                    should_stop = True
                                    success = True
                                    break
                            try:
                                if self.tools is not None:
                                    self.parse_and_execute_tools(response)
                            except Exception as e:
                                logger.error(
                                    f"Error executing tools: {e}"
                                )

                        # Add the response to the memory
                        self.short_memory.add(
                            role=self.agent_name, content=response
                        )

                        # Add to all responses
                        all_responses.append(response)

                        # # TODO: Implement reliability check

                        if self.evaluator:
                            logger.info("Evaluating response...")
                            evaluated_response = self.evaluator(
                                response
                            )
                            print(
                                "Evaluated Response:"
                                f" {evaluated_response}"
                            )
                            self.short_memory.add(
                                role="Evaluator",
                                content=evaluated_response,
                            )

                        # Sentiment analysis
                        if self.sentiment_analyzer:
                            logger.info("Analyzing sentiment...")
                            self.sentiment_analysis_handler(response)

                        success = True  # Mark as successful to exit the retry loop

                    except Exception as e:
                        if self.autosave is True:
                            self.save()

                        logger.error(
                            f"Attempt {attempt + 1}: Error generating"
                            f" response: {e}"
                        )
                        attempt += 1

                if not success:

                    if self.autosave is True:
                        self.save()

                    logger.error(
                        "Failed to generate a valid response after"
                        " retry attempts."
                    )
                    break  # Exit the loop if all retry attempts fail
                if should_stop:
                    logger.warning(
                        "Stopping due to user input or other external"
                        " interruption."
                    )
                    break

                # Check stopping conditions
                if (
                        self.stopping_condition is not None
                        and self._check_stopping_condition(response)
                ):
                    logger.info("Stopping condition met.")
                    break
                elif (
                        self.stopping_func is not None
                        and self.stopping_func(response)
                ):
                    logger.info("Stopping function met.")
                    break

                if self.interactive:
                    logger.info("Interactive mode enabled.")
                    user_input = input("You: ")

                    # User-defined exit command
                    if (
                            user_input.lower()
                            == self.custom_exit_command.lower()
                    ):
                        print("Exiting as per user request.")
                        break

                    self.short_memory.add(
                        role=self.user_name, content=user_input
                    )

                if self.loop_interval:
                    logger.info(
                        f"Sleeping for {self.loop_interval} seconds"
                    )
                    time.sleep(self.loop_interval)

            if self.autosave is True:

                if self.autosave is True:
                    self.save()

            # Apply the cleaner function to the response
            if self.output_cleaner is not None:
                logger.info("Applying output cleaner to response.")
                response = self.output_cleaner(response)
                logger.info(
                    f"Response after output cleaner: {response}"
                )
                self.short_memory.add(
                    role="Output Cleaner",
                    content=response,
                )

            if self.agent_ops_on is True and is_last is True:
                self.check_end_session_agentops()

            # Merge all responses
            all_responses = [
                response
                for response in all_responses
                if response is not None
            ]

            self.agent_output.steps = self.short_memory.to_dict()
            self.agent_output.full_history = (
                self.short_memory.get_str()
            )
            self.agent_output.total_tokens = (
                self.tokenizer.count_tokens(
                    self.short_memory.get_str()
                )
            )

            # Handle artifacts
            if self.artifacts_on is True:
                self.handle_artifacts(
                    concat_strings(all_responses),
                    self.artifacts_output_path,
                    self.artifacts_file_extension,
                )

            if self.autosave is True:
                self.save()

            # More flexible output types
            if (
                    self.output_type == "string"
                    or self.output_type == "str"
            ):
                yield concat_strings(all_responses)
            elif self.output_type == "list":
                yield all_responses
            elif (
                    self.output_type == "json"
                    or self.return_step_meta is True
            ):
                yield self.agent_output.model_dump_json(indent=4)
            elif self.output_type == "csv":
                yield self.dict_to_csv(
                    self.agent_output.model_dump()
                )
            elif self.output_type == "dict":
                yield self.agent_output.model_dump()
            elif self.output_type == "yaml":
                yield yaml.safe_dump(
                    self.agent_output.model_dump(), sort_keys=False
                )
            elif self.return_history is True:
                history = self.short_memory.get_str()
                logger.info(f"{self.agent_name} History: {history}")
                yield history
            else:
                raise ValueError(
                    f"Invalid output type: {self.output_type}"
                )

        except Exception as error:
            self._handle_run_error(error)

        except KeyboardInterrupt as error:
            self._handle_run_error(error)

    async def call_llm_in_stream(self, task: str, *args, **kwargs) -> AsyncIterator[str]:
        """
        Calls the appropriate method on the `llm` object based on the given task.

        Args:
            task (str): The task to be performed by the `llm` object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            str: The result of the method call on the `llm` object.

        Raises:
            AttributeError: If no suitable method is found in the llm object.
            TypeError: If task is not a string or llm object is None.
            ValueError: If task is empty.
        """
        if not isinstance(task, str):
            raise TypeError("Task must be a string")

        if not task.strip():
            raise ValueError("Task cannot be empty")

        if self.llm is None:
            raise TypeError("LLM object cannot be None")

        try:
            async for out in self.llm.astream(task, *args, **kwargs):
                if isinstance(out, str):
                    yield out
                elif isinstance(out, BaseMessageChunk):
                    yield out.content
        except AttributeError as e:
            logger.error(
                f"Error calling LLM: {e} You need a class with a run(task: str) method"
            )
            raise e

    async def async_parse_and_execute_tools(self, response: str, *args, **kwargs):
        try:
            logger.info("Executing async tool...")
            direct_output = kwargs.get("direct_output", True)
            # try to Execute the tool and return a string
            whole_output = ""
            async for data in async_execute(
                    functions=self.async_tools,
                    json_string=response,
                    parse_md=True,
                    *args,
                    **kwargs,
            ):
                if direct_output:
                    yield data
                else:
                    whole_output += str(data)

            if direct_output:
                return

            # Add the output to the memory
            self.short_memory.add(
                role="Tool Executor",
                content=whole_output,
            )

        except Exception as error:
            logger.error(f"Error executing tool: {error}")
            raise error

    async def send_node_message(self, message: str) -> AsyncIterator[NodeMessage]:
        """Send a node message to the agent."""
        if self.should_send_node:
            yield NodeMessage(message=message)

    def add_memory_object(self, memory: MemoryObject):
        """Add a memory object to the agent's memory."""
        self.short_memory.add(
            role="History data",
            content=f"user: {memory.input}\n\nassistant: {memory.output}",
        )
