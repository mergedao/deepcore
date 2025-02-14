import concurrent.futures
from typing import List

import tiktoken


class TikToken:
    def __init__(
            self,
            model_name: str = "o200k_base",
    ):
        try:
            self.model_name = model_name
            self.encoding = tiktoken.get_encoding(model_name)
        except Exception as e:
            raise ValueError(
                f"Failed to initialize tokenizer with model '{model_name}': {str(e)}"
            )

    def encode(self, string: str) -> str:
        return self.encoding.encode(string)

    def decode(self, tokens: List[int]) -> str:
        return self.encoding.decode(tokens)

    def count_tokens(self, string: str) -> int:
        num_tokens = 0

        def count_tokens_in_chunk(chunk):
            nonlocal num_tokens
            num_tokens += len(self.encoding.encode(chunk))

        # Split the string into chunks for parallel processing
        chunks = [
            string[i: i + 1000] for i in range(0, len(string), 1000)
        ]

        # Create a ThreadPoolExecutor with maximum threads
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=10
        ) as executor:
            # Submit each chunk for processing
            futures = [
                executor.submit(count_tokens_in_chunk, chunk)
                for chunk in chunks
            ]

            # Wait for all futures to complete
            concurrent.futures.wait(futures)

        return num_tokens
