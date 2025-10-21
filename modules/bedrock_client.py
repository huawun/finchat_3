"""
AWS Bedrock client for interacting with Claude 3.5 Sonnet.
"""

import json
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

from config import Config

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for AWS Bedrock service to interact with Claude models."""
    
    def __init__(self):
        """Initialize Bedrock client with AWS credentials."""
        try:
            self.client = boto3.client(
                service_name='bedrock-runtime',
                **Config.get_aws_credentials()
            )
            self.model_id = Config.BEDROCK_MODEL_ID
            self.max_tokens = Config.BEDROCK_MAX_TOKENS
            self.temperature = Config.BEDROCK_TEMPERATURE
            logger.info("Bedrock client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def generate_sql(
        self,
        user_query: str,
        schema_info: Dict[str, Any]
    ) -> str:
        """
        Generate SQL query from natural language using Claude.
        
        Args:
            user_query: User's natural language question
            schema_info: Database schema information
            
        Returns:
            str: Generated SQL query
            
        Raises:
            Exception: If SQL generation fails
        """
        prompt = self._build_sql_generation_prompt(user_query, schema_info)
        
        try:
            response = self._invoke_model(prompt)
            sql = self._extract_sql_from_response(response)
            logger.info(f"Generated SQL: {sql}")
            return sql
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            raise
    
    def format_response(
        self,
        sql_query: str,
        query_results: list,
        user_query: str
    ) -> str:
        """
        Format query results into natural language response.
        
        Args:
            sql_query: The SQL query that was executed
            query_results: Results from the database
            user_query: Original user question
            
        Returns:
            str: Natural language formatted response
        """
        prompt = self._build_response_formatting_prompt(
            sql_query,
            query_results,
            user_query
        )
        
        try:
            response = self._invoke_model(prompt)
            return response
        except Exception as e:
            logger.error(f"Response formatting failed: {e}")
            # Return a basic response if formatting fails
            return self._create_fallback_response(query_results)
    
    def _invoke_model(self, prompt: str) -> str:
        """
        Invoke Claude model with the given prompt.
        
        Args:
            prompt: The prompt to send to Claude
            
        Returns:
            str: Model response text
            
        Raises:
            ClientError: If API call fails
        """
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            raise
    
    def _build_sql_generation_prompt(
        self,
        user_query: str,
        schema_info: Dict[str, Any]
    ) -> str:
        """
        Build prompt for SQL generation.
        
        Args:
            user_query: User's question
            schema_info: Database schema
            
        Returns:
            str: Formatted prompt
        """
        schema_text = self._format_schema_info(schema_info)
        
        prompt = (
            f"""You are a SQL expert. Generate a valid SQL query """
            f"""for the following request.

Database Schema:
{schema_text}

User Request: {user_query}

Rules:
- Only use SELECT statements (no INSERT, UPDATE, DELETE, DROP)
- Use appropriate JOINs when needed
- Include LIMIT clause to prevent large result sets """
            f"""(max {Config.MAX_RESULT_ROWS} rows)
- Return valid PostgreSQL/RedShift syntax
- Use table and column names exactly as shown in the schema
- If the question is ambiguous, make reasonable assumptions

Return ONLY the SQL query without any explanation, """
            f"""markdown formatting, or code blocks. Just the raw SQL."""
        )
        return prompt
    
    def _build_response_formatting_prompt(
        self,
        sql_query: str,
        query_results: list,
        user_query: str
    ) -> str:
        """
        Build prompt for response formatting.
        
        Args:
            sql_query: Executed SQL query
            query_results: Query results
            user_query: Original user question
            
        Returns:
            str: Formatted prompt
        """
        # Limit results shown to first 10 rows for prompt
        results_sample = query_results[:10] if query_results else []
        total_rows = len(query_results)
        
        prompt = (
            f"""Format the following database query results into """
            f"""a clear, natural language response.

User Question: {user_query}

SQL Query Executed:
{sql_query}

Query Results ({total_rows} row(s) total):
{json.dumps(results_sample, indent=2, default=str)}

Instructions:
- Provide a clear, concise explanation of what the data shows
- Answer the user's original question directly
- If there are many results, summarize the key findings
- Use natural language, not technical jargon
- Be conversational and helpful
- If no results were found, explain that clearly

Format your response in plain text without markdown formatting."""
        )
        return prompt
    
    def _format_schema_info(self, schema_info: Dict[str, Any]) -> str:
        """
        Format schema information for prompt.
        
        Args:
            schema_info: Schema dictionary
            
        Returns:
            str: Formatted schema text
        """
        if not schema_info or 'tables' not in schema_info:
            return "No schema information available"
        
        schema_lines = []
        for table in schema_info['tables']:
            table_name = table['name']
            columns = table.get('columns', [])
            
            if columns:
                col_definitions = ', '.join([
                    f"{col['name']} ({col['type']})"
                    for col in columns
                ])
                schema_lines.append(f"{table_name}: {col_definitions}")
            else:
                schema_lines.append(table_name)
        
        return '\n'.join(schema_lines)
    
    def _extract_sql_from_response(self, response: str) -> str:
        """
        Extract SQL query from model response.
        
        Args:
            response: Model response text
            
        Returns:
            str: Cleaned SQL query
        """
        # Remove markdown code blocks if present
        sql = response.strip()
        
        # Remove ```sql and ``` if present
        if sql.startswith('```'):
            sql = sql.split('\n', 1)[1] if '\n' in sql else sql
            if sql.endswith('```'):
                sql = sql.rsplit('```', 1)[0]
        
        # Remove leading/trailing whitespace
        sql = sql.strip()
        
        return sql
    
    def _create_fallback_response(self, query_results: list) -> str:
        """
        Create a basic fallback response if formatting fails.
        
        Args:
            query_results: Query results
            
        Returns:
            str: Basic response text
        """
        if not query_results:
            return "No results found for your query."
        
        count = len(query_results)
        return f"Found {count} result(s). Please see the data table below."
    
    def test_connection(self) -> bool:
        """
        Test connection to Bedrock service.
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Simple test prompt
            response = self._invoke_model("Respond with 'OK'")
            return bool(response)
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {e}")
            return False