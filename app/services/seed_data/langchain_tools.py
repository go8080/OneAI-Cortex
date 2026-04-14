"""Declarative mapping of LangChain tools to categories.

Each tool entry includes:
- name: Unique tool name (referenced in agent config)
- description: Human-readable description for the catalog
- langchain_class: Fully qualified class path for dynamic import
- required_keys: List of API key names the tool needs
- input_schema: Describes what query/parameters the tool accepts
- schema_def: Tool input/output contract

Organized by ToolCategory enum values. Curated subset — expand in patch releases.
"""

from __future__ import annotations

from typing import Any

TOOL_CATALOG: dict[str, list[dict[str, Any]]] = {
    # ─── Search ──────────────────────────────────────────────────────
    "search": [
        {
            "name": "tavily_search",
            "description": "AI-powered search engine that returns relevant results with snippets and URLs",
            "langchain_class": "langchain_community.tools.tavily_search.TavilySearchResults",
            "required_keys": ["tavily_api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "Search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "list[{title, url, content}]"},
        },
        {
            "name": "ddg_search",
            "description": "DuckDuckGo search — no API key required, privacy-focused web search",
            "langchain_class": "langchain_community.tools.ddg_search.tool.DuckDuckGoSearchRun",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "Search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "ddg_search_results",
            "description": "DuckDuckGo search returning structured results with snippets and links",
            "langchain_class": "langchain_community.tools.ddg_search.tool.DuckDuckGoSearchResults",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "Search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "list[{snippet, title, link}]"},
        },
        {
            "name": "brave_search",
            "description": "Brave Search API — independent web search with privacy focus",
            "langchain_class": "langchain_community.tools.brave_search.tool.BraveSearch",
            "required_keys": ["api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "Search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "searx_search",
            "description": "SearxNG meta-search engine — aggregates results from multiple search engines",
            "langchain_class": "langchain_community.tools.searx_search.tool.SearxSearchRun",
            "required_keys": ["searx_host"],
            "input_schema": {
                "query": {"type": "string", "description": "Search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
    # ─── Research ────────────────────────────────────────────────────
    "research": [
        {
            "name": "arxiv_search",
            "description": "Search academic papers on arXiv.org by topic, author, or ID",
            "langchain_class": "langchain_community.tools.arxiv.tool.ArxivQueryRun",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "Search query or arXiv paper ID", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "pubmed_search",
            "description": "Search PubMed biomedical literature database",
            "langchain_class": "langchain_community.tools.pubmed.tool.PubmedQueryRun",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "Biomedical search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "wikipedia_search",
            "description": "Search and retrieve Wikipedia article summaries",
            "langchain_class": "langchain_community.tools.wikipedia.tool.WikipediaQueryRun",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "Wikipedia search term", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "google_scholar_search",
            "description": "Search Google Scholar for academic papers and citations",
            "langchain_class": "langchain_community.tools.google_scholar.tool.GoogleScholarQueryRun",
            "required_keys": ["serp_api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "Academic search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "stackexchange_search",
            "description": "Search Stack Exchange network for programming and technical Q&A",
            "langchain_class": "langchain_community.tools.stackexchange.tool.StackExchangeTool",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "Technical question", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
    # ─── Browser ─────────────────────────────────────────────────────
    "browser": [
        {
            "name": "browser_navigate",
            "description": "Navigate to a URL in a browser automation session",
            "langchain_class": "langchain_community.tools.playwright.navigate.NavigateTool",
            "required_keys": [],
            "input_schema": {
                "url": {"type": "string", "description": "URL to navigate to", "required": True},
            },
            "schema_def": {"input": {"url": "string"}, "output": "string"},
        },
        {
            "name": "browser_extract_text",
            "description": "Extract all visible text from the current browser page",
            "langchain_class": "langchain_community.tools.playwright.extract_text.ExtractTextTool",
            "required_keys": [],
            "input_schema": {},
            "schema_def": {"input": {}, "output": "string"},
        },
        {
            "name": "browser_extract_links",
            "description": "Extract all hyperlinks from the current browser page",
            "langchain_class": "langchain_community.tools.playwright.extract_hyperlinks.ExtractHyperlinksTool",
            "required_keys": [],
            "input_schema": {},
            "schema_def": {"input": {}, "output": "list[{text, url}]"},
        },
        {
            "name": "browser_click",
            "description": "Click an element on the current page by CSS selector",
            "langchain_class": "langchain_community.tools.playwright.click.ClickTool",
            "required_keys": [],
            "input_schema": {
                "selector": {"type": "string", "description": "CSS selector of element to click", "required": True},
            },
            "schema_def": {"input": {"selector": "string"}, "output": "string"},
        },
    ],
    # ─── Communication ───────────────────────────────────────────────
    "communication": [
        {
            "name": "gmail_send_message",
            "description": "Send an email via Gmail API. Requires Google Connected Services.",
            "langchain_class": "langchain_community.tools.gmail.send_message.GmailSendMessage",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "to": {"type": "string", "description": "Recipient email", "required": True},
                "subject": {"type": "string", "description": "Email subject", "required": True},
                "message": {"type": "string", "description": "Email body", "required": True},
            },
            "schema_def": {"input": {"to": "string", "subject": "string", "message": "string"}, "output": "string"},
        },
        {
            "name": "gmail_search",
            "description": "Search Gmail inbox with query filters. Requires Google Connected Services.",
            "langchain_class": "langchain_community.tools.gmail.search.GmailSearch",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "query": {"type": "string", "description": "Gmail search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "list[{id, subject, snippet}]"},
        },
        {
            "name": "gmail_get_message",
            "description": "Get a specific email message by ID. Requires Google Connected Services.",
            "langchain_class": "langchain_community.tools.gmail.get_message.GmailGetMessage",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "message_id": {"type": "string", "description": "Gmail message ID", "required": True},
            },
            "schema_def": {"input": {"message_id": "string"}, "output": "string"},
        },
        {
            "name": "gmail_create_draft",
            "description": "Create an email draft in Gmail. Requires Google Connected Services.",
            "langchain_class": "langchain_community.tools.gmail.create_draft.GmailCreateDraft",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "to": {"type": "string", "description": "Recipient email", "required": True},
                "subject": {"type": "string", "description": "Email subject", "required": True},
                "message": {"type": "string", "description": "Email body", "required": True},
            },
            "schema_def": {"input": {"to": "string", "subject": "string", "message": "string"}, "output": "string"},
        },
        {
            "name": "slack_send_message",
            "description": "Send a message to a Slack channel",
            "langchain_class": "langchain_community.tools.slack.send_message.SlackSendMessage",
            "required_keys": [],
            "input_schema": {
                "channel": {"type": "string", "description": "Slack channel name or ID", "required": True},
                "message": {"type": "string", "description": "Message text", "required": True},
            },
            "schema_def": {"input": {"channel": "string", "message": "string"}, "output": "string"},
        },
        {
            "name": "slack_get_channel",
            "description": "Get information about a Slack channel",
            "langchain_class": "langchain_community.tools.slack.get_channel.SlackGetChannel",
            "required_keys": [],
            "input_schema": {
                "channel": {"type": "string", "description": "Channel name or ID", "required": True},
            },
            "schema_def": {"input": {"channel": "string"}, "output": "string"},
        },
    ],
    # ─── DevTools ────────────────────────────────────────────────────
    "devtools": [
        {
            "name": "shell_tool",
            "description": "Execute shell commands on the host system",
            "langchain_class": "langchain_community.tools.shell.tool.ShellTool",
            "required_keys": [],
            "input_schema": {
                "command": {"type": "string", "description": "Shell command to execute", "required": True},
            },
            "schema_def": {"input": {"command": "string"}, "output": "string"},
        },
        {
            "name": "requests_get",
            "description": "Make HTTP GET requests to any URL",
            "langchain_class": "langchain_community.tools.requests.tool.RequestsGetTool",
            "required_keys": [],
            "input_schema": {
                "url": {"type": "string", "description": "URL to request", "required": True},
            },
            "schema_def": {"input": {"url": "string"}, "output": "string"},
        },
        {
            "name": "requests_post",
            "description": "Make HTTP POST requests with a JSON body",
            "langchain_class": "langchain_community.tools.requests.tool.RequestsPostTool",
            "required_keys": [],
            "input_schema": {
                "url": {"type": "string", "description": "URL to request", "required": True},
                "body": {"type": "object", "description": "JSON body", "required": True},
            },
            "schema_def": {"input": {"url": "string", "body": "object"}, "output": "string"},
        },
        {
            "name": "graphql_query",
            "description": "Execute GraphQL queries against an API endpoint",
            "langchain_class": "langchain_community.tools.graphql.tool.BaseGraphQLTool",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "GraphQL query string", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
    # ─── Files ───────────────────────────────────────────────────────
    "files": [
        {
            "name": "read_file",
            "description": "Read the contents of a file from the filesystem",
            "langchain_class": "langchain_community.tools.file_management.read.ReadFileTool",
            "required_keys": [],
            "input_schema": {
                "file_path": {"type": "string", "description": "Path to file", "required": True},
            },
            "schema_def": {"input": {"file_path": "string"}, "output": "string"},
        },
        {
            "name": "write_file",
            "description": "Write content to a file on the filesystem",
            "langchain_class": "langchain_community.tools.file_management.write.WriteFileTool",
            "required_keys": [],
            "input_schema": {
                "file_path": {"type": "string", "description": "Path to file", "required": True},
                "text": {"type": "string", "description": "Content to write", "required": True},
            },
            "schema_def": {"input": {"file_path": "string", "text": "string"}, "output": "string"},
        },
        {
            "name": "list_directory",
            "description": "List files and directories at a given path",
            "langchain_class": "langchain_community.tools.file_management.list_dir.ListDirectoryTool",
            "required_keys": [],
            "input_schema": {
                "dir_path": {"type": "string", "description": "Directory path", "required": False, "default": "."},
            },
            "schema_def": {"input": {"dir_path": "string"}, "output": "string"},
        },
        {
            "name": "copy_file",
            "description": "Copy a file from source to destination",
            "langchain_class": "langchain_community.tools.file_management.copy.CopyFileTool",
            "required_keys": [],
            "input_schema": {
                "source_path": {"type": "string", "description": "Source file path", "required": True},
                "destination_path": {"type": "string", "description": "Destination path", "required": True},
            },
            "schema_def": {"input": {"source_path": "string", "destination_path": "string"}, "output": "string"},
        },
        {
            "name": "move_file",
            "description": "Move or rename a file",
            "langchain_class": "langchain_community.tools.file_management.move.MoveFileTool",
            "required_keys": [],
            "input_schema": {
                "source_path": {"type": "string", "description": "Source file path", "required": True},
                "destination_path": {"type": "string", "description": "Destination path", "required": True},
            },
            "schema_def": {"input": {"source_path": "string", "destination_path": "string"}, "output": "string"},
        },
        {
            "name": "google_drive_search",
            "description": "Search for files in Google Drive by name or query. Requires Google Connected Services.",
            "langchain_class": "app.adapters.deepagents.google_tools.GoogleDriveSearch",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "query": {"type": "string", "description": "Search query (file name or Drive query)", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "list[{id, name, mimeType}]"},
        },
        {
            "name": "google_drive_read",
            "description": "Read a file's content from Google Drive by file ID. Requires Google Connected Services.",
            "langchain_class": "app.adapters.deepagents.google_tools.GoogleDriveRead",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "file_id": {"type": "string", "description": "Google Drive file ID", "required": True},
            },
            "schema_def": {"input": {"file_id": "string"}, "output": "string"},
        },
    ],
    # ─── Database ────────────────────────────────────────────────────
    "database": [
        {
            "name": "sql_query",
            "description": "Execute SQL queries against a database",
            "langchain_class": "langchain_community.tools.sql_database.tool.QuerySQLDataBaseTool",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "SQL query to execute", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "sql_list_tables",
            "description": "List all tables in the connected database",
            "langchain_class": "langchain_community.tools.sql_database.tool.ListSQLDatabaseTool",
            "required_keys": [],
            "input_schema": {},
            "schema_def": {"input": {}, "output": "string"},
        },
        {
            "name": "sql_schema_info",
            "description": "Get schema information for specified database tables",
            "langchain_class": "langchain_community.tools.sql_database.tool.InfoSQLDatabaseTool",
            "required_keys": [],
            "input_schema": {
                "table_names": {"type": "string", "description": "Comma-separated table names", "required": True},
            },
            "schema_def": {"input": {"table_names": "string"}, "output": "string"},
        },
    ],
    # ─── Data Analysis ───────────────────────────────────────────────
    "data_analysis": [
        {
            "name": "e2b_data_analysis",
            "description": "Execute Python code in a sandboxed E2B environment for data analysis",
            "langchain_class": "langchain_community.tools.e2b_data_analysis.tool.E2BDataAnalysisTool",
            "required_keys": ["e2b_api_key"],
            "input_schema": {
                "python_code": {"type": "string", "description": "Python code to execute", "required": True},
            },
            "schema_def": {"input": {"python_code": "string"}, "output": "string"},
        },
        {
            "name": "json_get_value",
            "description": "Extract a value from a JSON blob by path",
            "langchain_class": "langchain_community.tools.json_tool.tool.JsonGetValueTool",
            "required_keys": [],
            "input_schema": {
                "path": {"type": "string", "description": "JSON path (e.g., data.users[0].name)", "required": True},
            },
            "schema_def": {"input": {"path": "string"}, "output": "string"},
        },
        {
            "name": "json_list_keys",
            "description": "List all keys in a JSON object at a given path",
            "langchain_class": "langchain_community.tools.json_tool.tool.JsonListKeysTool",
            "required_keys": [],
            "input_schema": {
                "path": {"type": "string", "description": "JSON path to inspect", "required": False},
            },
            "schema_def": {"input": {"path": "string"}, "output": "string"},
        },
    ],
    # ─── Speech & Audio ──────────────────────────────────────────────
    "speech_audio": [
        {
            "name": "eleven_labs_tts",
            "description": "Convert text to speech using ElevenLabs API",
            "langchain_class": "langchain_community.tools.eleven_labs.text2speech.ElevenLabsText2SpeechTool",
            "required_keys": ["eleven_api_key"],
            "input_schema": {
                "text": {"type": "string", "description": "Text to convert to speech", "required": True},
            },
            "schema_def": {"input": {"text": "string"}, "output": "string (audio file path)"},
        },
        {
            "name": "google_cloud_tts",
            "description": "Convert text to speech using Google Cloud Text-to-Speech",
            "langchain_class": "langchain_community.tools.google_cloud.texttospeech.GoogleCloudTextToSpeechTool",
            "required_keys": [],
            "input_schema": {
                "text": {"type": "string", "description": "Text to convert to speech", "required": True},
            },
            "schema_def": {"input": {"text": "string"}, "output": "string (audio file path)"},
        },
        {
            "name": "azure_speech_to_text",
            "description": "Convert speech audio to text using Azure Cognitive Services",
            "langchain_class": "langchain_community.tools.azure_cognitive_services.speech2text.AzureCogsSpeech2TextTool",
            "required_keys": ["azure_cogs_key", "azure_cogs_region"],
            "input_schema": {
                "audio_path": {"type": "string", "description": "Path to audio file", "required": True},
            },
            "schema_def": {"input": {"audio_path": "string"}, "output": "string"},
        },
    ],
    # ─── Image & Vision ──────────────────────────────────────────────
    "image_vision": [
        {
            "name": "azure_image_analysis",
            "description": "Analyze images using Azure Cognitive Services Computer Vision",
            "langchain_class": "langchain_community.tools.azure_cognitive_services.image_analysis.AzureCogsImageAnalysisTool",
            "required_keys": ["azure_cogs_key", "azure_cogs_region"],
            "input_schema": {
                "image_url": {"type": "string", "description": "URL of the image to analyze", "required": True},
            },
            "schema_def": {"input": {"image_url": "string"}, "output": "string"},
        },
        {
            "name": "scenexplain",
            "description": "Advanced image scene understanding and description",
            "langchain_class": "langchain_community.tools.scenexplain.tool.SceneXplainTool",
            "required_keys": ["scenex_api_key"],
            "input_schema": {
                "image_url": {"type": "string", "description": "URL of the image", "required": True},
            },
            "schema_def": {"input": {"image_url": "string"}, "output": "string"},
        },
        {
            "name": "google_lens",
            "description": "Search and identify objects in images using Google Lens",
            "langchain_class": "langchain_community.tools.google_lens.tool.GoogleLensQueryRun",
            "required_keys": ["serp_api_key"],
            "input_schema": {
                "image_url": {"type": "string", "description": "URL of the image", "required": True},
            },
            "schema_def": {"input": {"image_url": "string"}, "output": "string"},
        },
    ],
    # ─── Documents ───────────────────────────────────────────────────
    "documents": [
        {
            "name": "azure_form_recognizer",
            "description": "Extract text and structure from documents using Azure Form Recognizer (OCR)",
            "langchain_class": "langchain_community.tools.azure_cognitive_services.form_recognizer.AzureCogsFormRecognizerTool",
            "required_keys": ["azure_cogs_key", "azure_cogs_region"],
            "input_schema": {
                "document_url": {"type": "string", "description": "URL of the document", "required": True},
            },
            "schema_def": {"input": {"document_url": "string"}, "output": "string"},
        },
        {
            "name": "edenai_invoice_parser",
            "description": "Parse invoice documents and extract structured data",
            "langchain_class": "langchain_community.tools.edenai.edenai_tools.EdenAiParsingInvoiceTool",
            "required_keys": ["edenai_api_key"],
            "input_schema": {
                "document_url": {"type": "string", "description": "URL of the invoice", "required": True},
            },
            "schema_def": {"input": {"document_url": "string"}, "output": "string"},
        },
        {
            "name": "edenai_id_parser",
            "description": "Parse identity documents (passport, ID card) and extract data",
            "langchain_class": "langchain_community.tools.edenai.edenai_tools.EdenAiParsingIDTool",
            "required_keys": ["edenai_api_key"],
            "input_schema": {
                "document_url": {"type": "string", "description": "URL of the ID document", "required": True},
            },
            "schema_def": {"input": {"document_url": "string"}, "output": "string"},
        },
    ],
    # ─── Moderation ──────────────────────────────────────────────────
    "moderation": [
        {
            "name": "edenai_text_moderation",
            "description": "Moderate text content for harmful, offensive, or inappropriate material",
            "langchain_class": "langchain_community.tools.edenai.edenai_tools.EdenAiTextModerationTool",
            "required_keys": ["edenai_api_key"],
            "input_schema": {
                "text": {"type": "string", "description": "Text to moderate", "required": True},
            },
            "schema_def": {"input": {"text": "string"}, "output": "string"},
        },
        {
            "name": "edenai_explicit_image",
            "description": "Detect explicit or inappropriate content in images",
            "langchain_class": "langchain_community.tools.edenai.edenai_tools.EdenAiExplicitImageTool",
            "required_keys": ["edenai_api_key"],
            "input_schema": {
                "image_url": {"type": "string", "description": "URL of the image to check", "required": True},
            },
            "schema_def": {"input": {"image_url": "string"}, "output": "string"},
        },
    ],
    # ─── Weather & Location ──────────────────────────────────────────
    "weather_location": [
        {
            "name": "openweathermap",
            "description": "Get current weather data for any location",
            "langchain_class": "langchain_community.tools.openweathermap.tool.OpenWeatherMapQueryRun",
            "required_keys": ["openweathermap_api_key"],
            "input_schema": {
                "location": {"type": "string", "description": "City name or coordinates", "required": True},
            },
            "schema_def": {"input": {"location": "string"}, "output": "string"},
        },
        {
            "name": "google_places",
            "description": "Search for local businesses and places via Google Places API",
            "langchain_class": "langchain_community.tools.google_places.tool.GooglePlacesTool",
            "required_keys": ["gplaces_api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "Place search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
    # ─── Finance ─────────────────────────────────────────────────────
    "finance": [
        {
            "name": "google_finance",
            "description": "Get stock prices, market data, and financial information",
            "langchain_class": "langchain_community.tools.google_finance.tool.GoogleFinanceQueryRun",
            "required_keys": ["serp_api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "Stock ticker or financial query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
    # ─── Travel ──────────────────────────────────────────────────────
    "travel": [
        {
            "name": "amadeus_flight_search",
            "description": "Search for flights between airports using Amadeus API",
            "langchain_class": "langchain_community.tools.amadeus.flight_search.AmadeusFlightSearch",
            "required_keys": ["amadeus_client_id", "amadeus_client_secret"],
            "input_schema": {
                "origin": {"type": "string", "description": "Origin airport code (IATA)", "required": True},
                "destination": {"type": "string", "description": "Destination airport code", "required": True},
                "departure_date": {"type": "string", "description": "Date (YYYY-MM-DD)", "required": True},
            },
            "schema_def": {"input": {"origin": "string", "destination": "string", "departure_date": "string"}, "output": "string"},
        },
        {
            "name": "amadeus_closest_airport",
            "description": "Find the closest airport to a city or coordinates",
            "langchain_class": "langchain_community.tools.amadeus.closest_airport.AmadeusClosestAirport",
            "required_keys": ["amadeus_client_id", "amadeus_client_secret"],
            "input_schema": {
                "location": {"type": "string", "description": "City name or coordinates", "required": True},
            },
            "schema_def": {"input": {"location": "string"}, "output": "string"},
        },
    ],
    # ─── Media ───────────────────────────────────────────────────────
    "media": [
        {
            "name": "youtube_search",
            "description": "Search YouTube for videos by keyword",
            "langchain_class": "langchain_community.tools.youtube.search.YouTubeSearchTool",
            "required_keys": [],
            "input_schema": {
                "query": {"type": "string", "description": "YouTube search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "google_trends",
            "description": "Analyze search trends and trending topics via Google Trends",
            "langchain_class": "langchain_community.tools.google_trends.tool.GoogleTrendsQueryRun",
            "required_keys": ["serp_api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "Trend search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
    # ─── Science ─────────────────────────────────────────────────────
    "science": [
        {
            "name": "wolfram_alpha",
            "description": "Computational knowledge engine — math, science, data analysis queries",
            "langchain_class": "langchain_community.tools.wolfram_alpha.tool.WolframAlphaQueryRun",
            "required_keys": ["wolfram_alpha_appid"],
            "input_schema": {
                "query": {"type": "string", "description": "Computational query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
        {
            "name": "nasa_action",
            "description": "Access NASA APIs — astronomy picture of the day, Mars rover photos, etc.",
            "langchain_class": "langchain_community.tools.nasa.tool.NasaAction",
            "required_keys": ["nasa_api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "NASA API action", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
    # ─── Automation ──────────────────────────────────────────────────
    "automation": [
        {
            "name": "zapier_run_action",
            "description": "Run Zapier NLA actions — trigger workflows across 5000+ apps",
            "langchain_class": "langchain_community.tools.zapier.tool.ZapierNLARunAction",
            "required_keys": ["zapier_nla_api_key"],
            "input_schema": {
                "instructions": {"type": "string", "description": "Natural language instructions for the action", "required": True},
            },
            "schema_def": {"input": {"instructions": "string"}, "output": "string"},
        },
        {
            "name": "zapier_list_actions",
            "description": "List all available Zapier NLA actions",
            "langchain_class": "langchain_community.tools.zapier.tool.ZapierNLAListActions",
            "required_keys": ["zapier_nla_api_key"],
            "input_schema": {},
            "schema_def": {"input": {}, "output": "string"},
        },
        {
            "name": "sleep_tool",
            "description": "Pause execution for a specified duration (useful in agent workflows)",
            "langchain_class": "langchain_community.tools.sleep.tool.SleepTool",
            "required_keys": [],
            "input_schema": {
                "duration": {"type": "integer", "description": "Sleep duration in seconds", "required": True},
            },
            "schema_def": {"input": {"duration": "integer"}, "output": "string"},
        },
        {
            "name": "google_calendar_list_events",
            "description": "List upcoming events from Google Calendar. Requires Google Connected Services.",
            "langchain_class": "app.adapters.deepagents.google_tools.GoogleCalendarListEvents",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "max_results": {"type": "integer", "description": "Max events to return", "required": False, "default": 10},
                "time_min": {"type": "string", "description": "Start time (ISO 8601)", "required": False},
            },
            "schema_def": {"input": {"max_results": "integer", "time_min": "string"}, "output": "list[{summary, start, end}]"},
        },
        {
            "name": "google_calendar_create_event",
            "description": "Create a new event on Google Calendar. Requires Google Connected Services.",
            "langchain_class": "app.adapters.deepagents.google_tools.GoogleCalendarCreateEvent",
            "required_keys": [],
            "auth_type": "google_oauth",
            "input_schema": {
                "summary": {"type": "string", "description": "Event title", "required": True},
                "start_time": {"type": "string", "description": "Start time (ISO 8601)", "required": True},
                "end_time": {"type": "string", "description": "End time (ISO 8601)", "required": True},
                "description": {"type": "string", "description": "Event description", "required": False},
            },
            "schema_def": {"input": {"summary": "string", "start_time": "string", "end_time": "string"}, "output": "string"},
        },
    ],
    # ─── Blockchain ──────────────────────────────────────────────────
    "blockchain": [
        {
            "name": "ainetwork_transfer",
            "description": "Transfer tokens on the AI Network blockchain",
            "langchain_class": "langchain_community.tools.ainetwork.transfer.AINTransfer",
            "required_keys": ["ain_blockchain_account"],
            "input_schema": {
                "to": {"type": "string", "description": "Recipient address", "required": True},
                "amount": {"type": "number", "description": "Amount to transfer", "required": True},
            },
            "schema_def": {"input": {"to": "string", "amount": "number"}, "output": "string"},
        },
        {
            "name": "ainetwork_value_ops",
            "description": "Read and write values on the AI Network blockchain database",
            "langchain_class": "langchain_community.tools.ainetwork.value.AINValueOps",
            "required_keys": ["ain_blockchain_account"],
            "input_schema": {
                "path": {"type": "string", "description": "Database path", "required": True},
            },
            "schema_def": {"input": {"path": "string"}, "output": "string"},
        },
    ],
    # ─── Utility ─────────────────────────────────────────────────────
    "utility": [
        {
            "name": "human_input",
            "description": "Request input from a human user during agent execution",
            "langchain_class": "langchain_community.tools.human.tool.HumanInputRun",
            "required_keys": [],
            "input_schema": {
                "prompt": {"type": "string", "description": "Question or prompt for the human", "required": True},
            },
            "schema_def": {"input": {"prompt": "string"}, "output": "string"},
        },
        {
            "name": "merriam_webster",
            "description": "Look up word definitions, synonyms, and pronunciation",
            "langchain_class": "langchain_community.tools.merriam_webster.tool.MerriamWebsterQueryRun",
            "required_keys": ["merriam_webster_api_key"],
            "input_schema": {
                "word": {"type": "string", "description": "Word to look up", "required": True},
            },
            "schema_def": {"input": {"word": "string"}, "output": "string"},
        },
        {
            "name": "google_jobs",
            "description": "Search job listings via Google Jobs",
            "langchain_class": "langchain_community.tools.google_jobs.tool.GoogleJobsQueryRun",
            "required_keys": ["serp_api_key"],
            "input_schema": {
                "query": {"type": "string", "description": "Job search query", "required": True},
            },
            "schema_def": {"input": {"query": "string"}, "output": "string"},
        },
    ],
}
