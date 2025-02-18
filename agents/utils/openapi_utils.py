import copy
import json
import logging
from typing import Dict, Any, Tuple

from prance import ResolvingParser

# Constants for parameter type suffixes
HEADER_SUFFIX = '_by_header'
PARAMS_SUFFIX = '_by_params'
PATH_SUFFIX = '_by_paths'

# Fields to be filtered out from OpenAPI spec
filtered_fields = ['testcase']

logger = logging.getLogger(__name__)


def load_openapi_spec(spec_json: str) -> Dict[str, Any]:
    """
    Load and parse OpenAPI specification
    Filter unnecessary fields and handle streaming connections
    """
    try:
        parsed_json = json.loads(spec_json)
        filtered_spec = filter_specification_fields(parsed_json)
        filtered_json = json.dumps(filtered_spec, ensure_ascii=False)
    except Exception as e:
        logger.warning(f'Field filtering failed: {e}', exc_info=True)
    parser = ResolvingParser(spec_string=filtered_json, skip_validation=True)
    return parser.specification


def filter_specification_fields(specification: Dict[str, Any]):
    """
    Remove unnecessary fields from OpenAPI specification
    """
    spec_copy = specification.copy()
    if isinstance(specification, dict):
        for key in specification.keys():
            if key in filtered_fields:
                del spec_copy[key]
            elif isinstance(specification[key], dict):
                spec_copy[key] = filter_specification_fields(specification[key])
    return spec_copy


def generate_schema_model(schema: Dict[str, Any]) -> Dict:
    """
    Recursively parse schema to generate a dictionary model
    """
    property_fields = {}
    for prop_name, prop_spec in schema.get('properties', {}).items():
        field_definition = {}
        field_type = prop_spec.get('type')
        field_definition['type'] = field_type
        
        if prop_spec.get('default') is not None:
            field_definition['default'] = prop_spec['default']
        if prop_spec.get('required'):
            field_definition['required'] = prop_spec['required']
        field_definition['description'] = prop_spec.get('description', '')
        
        if field_type == 'array' and 'items' in prop_spec:
            field_definition['items'] = generate_schema_model(prop_spec['items'])
        elif field_type == 'object' and 'properties' in prop_spec:
            field_definition['properties'] = generate_schema_model(prop_spec)
            
        property_fields[prop_name] = field_definition

    schema_model = {
        'type': schema.get('type', ''),
        'properties': property_fields
    }

    if schema.get('description'):
        schema_model['description'] = schema['description']
    if schema.get('required'):
        schema_model['required'] = schema['required']

    return schema_model


def parse_parameters(parameters: Dict[Dict, Any]) -> Tuple[Dict, Dict, Dict]:
    """
    Parse OpenAPI parameters and extract headers, query params, and path params
    """
    header_params, query_params, path_params = {}, {}, {}
    
    for param in parameters:
        param_definition = {
            'type': param.get('schema', {}).get('type', 'string'),
            'description': param.get('description', '')
        }
        
        if param.get('schema', {}).get('default') is not None:
            param_definition['default'] = param.get('schema', {}).get('default')
        if param.get('required'):
            param_definition['required'] = param.get('required')
            
        param_location = param.get('in', '')
        param_name = param['name']
        
        if param_location == 'header':
            header_params[param_name] = param_definition
        elif param_location == 'path':
            path_params[param_name] = param_definition
        else:
            query_params[param_name] = param_definition
            
    return header_params, query_params, path_params


def process_openapi_paths(openapi_spec: Dict[str, Any]) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Process paths in OpenAPI specification
    Extract headers, query params, path params, and request body schema
    """
    openapi_paths = openapi_spec.get('paths', {})
    header_params, query_params, path_params, request_schema = {}, {}, {}, {}

    for path, path_info in openapi_paths.items():
        for method, method_info in path_info.items():
            if not isinstance(method_info, dict):
                continue

            # Parse parameters
            parameters = method_info.get('parameters', [])
            header_params, query_params, path_params = parse_parameters(parameters)

            # Parse request body
            request_body_content = method_info.get('requestBody', {}).get('content', {})
            for content_type, media_type_object in request_body_content.items():
                schema = media_type_object.get('schema', {})
                if schema:
                    request_schema = generate_schema_model(schema)
                    break

    return header_params, query_params, path_params, request_schema


def merge_parameters(header_params: Dict, query_params: Dict, 
                    path_params: Dict, request_schema: Dict) -> Dict:
    """
    Merge all parameters into a single request schema
    Add appropriate suffixes to distinguish parameter types
    """
    merged_schema = copy.deepcopy(request_schema)
    required_fields = []
    merged_schema["properties"] = merged_schema.get('properties', {})

    # Merge header parameters
    for key, value in header_params.items():
        param_key = key + HEADER_SUFFIX
        merged_schema["properties"][param_key] = value
        if value.get('required'):
            required_fields.append(param_key)
            del value['required']

    # Merge query parameters
    for key, value in query_params.items():
        param_key = key + PARAMS_SUFFIX
        merged_schema["properties"][param_key] = value
        if value.get('required'):
            required_fields.append(param_key)
            del value['required']

    # Merge path parameters
    for key, value in path_params.items():
        param_key = key + PATH_SUFFIX
        merged_schema["properties"][param_key] = value
        if value.get('required'):
            required_fields.append(param_key)
            del value['required']

    if required_fields:
        merged_schema['required'] = merged_schema.get('required', []) + required_fields

    return merged_schema


def get_request_parameters(spec_json: str) -> Dict:
    """
    Extract and merge all parameters from OpenAPI specification
    """
    openapi_spec = load_openapi_spec(spec_json)
    header_params, query_params, path_params, request_schema = process_openapi_paths(openapi_spec)
    return merge_parameters(header_params, query_params, path_params, request_schema)


def parse_request_args(args: Dict) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Parse request arguments and separate them by parameter type
    """
    header_params, query_params, path_params, body_params = {}, {}, {}, {}
    
    if isinstance(args, dict):
        for key, value in args.items():
            if key.endswith(HEADER_SUFFIX):
                header_key = key[:-len(HEADER_SUFFIX)]
                header_params[header_key] = value
            elif key.endswith(PARAMS_SUFFIX):
                param_key = key[:-len(PARAMS_SUFFIX)]
                query_params[param_key] = value
            elif key.endswith(PATH_SUFFIX):
                path_key = key[:-len(PATH_SUFFIX)]
                path_params[path_key] = value
            else:
                body_params[key] = value
                
        return header_params, query_params, path_params, body_params
    return header_params, query_params, path_params, args


def apply_default_values(spec_json: str, header_args: Dict, query_args: Dict, path_args: Dict) -> Tuple[Dict, Dict, Dict]:
    """
    Apply default values from OpenAPI specification to parameters if not provided
    """
    try:
        openapi_spec = load_openapi_spec(spec_json)
        header_params, query_params, path_params, _ = process_openapi_paths(openapi_spec)

        # Apply defaults for header parameters
        for key, value in header_params.items():
            if (key not in header_args or not header_args[key]) and "default" in value:
                header_args[key] = value.get("default")

        # Apply defaults for query parameters
        for key, value in query_params.items():
            if (key not in query_args or not query_args[key]) and "default" in value:
                query_args[key] = value.get("default")

        # Apply defaults for path parameters
        for key, value in path_params.items():
            if (key not in path_args or not path_args[key]) and "default" in value:
                path_args[key] = value.get("default")

    except Exception as e:
        logger.error(f"Failed to apply default values: {e}", exc_info=True)

    return header_args, query_args, path_args

