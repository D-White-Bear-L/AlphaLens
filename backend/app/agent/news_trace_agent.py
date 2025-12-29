"""News trace agent using mira library."""
import asyncio
import json
import re
from typing import List, Optional, Callable

from loguru import logger
from mira import HumanMessage, OpenAIArgs, OpenRouterLLM, SystemMessage

from app.config import settings
from app.models import (
    NewsSource, TraceResult, TimelineEvent, CausalRelation, KnowledgeGraph, HierarchyGraph, HierarchyNode,
    TimelineOutput, CausalRelationsOutput, KnowledgeGraphOutput, HierarchyGraphOutput
)
from app.tools.google_search import GoogleSearch

# Try to import WebScraper, but make it optional
try:
    from app.tools.web_scraper import WebScraper, PLAYWRIGHT_AVAILABLE
    WEB_SCRAPER_AVAILABLE = PLAYWRIGHT_AVAILABLE
except (ImportError, AttributeError):
    WEB_SCRAPER_AVAILABLE = False
    WebScraper = None
    logger.warning("WebScraper tool not available (playwright not installed)")

# Try to import DatabaseSearch, but make it optional
try:
    from app.tools.database_search import DatabaseSearch, SQLALCHEMY_AVAILABLE
    DATABASE_SEARCH_AVAILABLE = SQLALCHEMY_AVAILABLE
except (ImportError, AttributeError):
    DATABASE_SEARCH_AVAILABLE = False
    DatabaseSearch = None
    logger.warning("DatabaseSearch tool not available (sqlalchemy not installed)")


class NewsTraceAgent:
    """Agent for tracing financial news sources."""
    
    def __init__(self):
        """Initialize the agent with LLM and tools."""
        # Initialize LLM with mira - use settings from .env file
        llm_args = OpenAIArgs(
            api_key=settings.get_api_key(),
            base_url=settings.get_base_url(),
            model=settings.model,
            temperature=0.7,
            max_completion_tokens=4000,  # Increased to avoid truncation for structured outputs
            verbose=True  # Enable verbose logging to see API requests/responses
        )
        self.llm = OpenRouterLLM(args=llm_args)
        logger.info(f"LLM initialized with model: {settings.model}, base_url: {settings.get_base_url()}")
        
        # Initialize tools (only include tools if dependencies are available)
        self.tools = [
            GoogleSearch,  # Always available
        ]
        
        # Add WebScraper only if playwright is available
        if WEB_SCRAPER_AVAILABLE:
            self.tools.append(WebScraper)
            logger.info("WebScraper tool enabled")
        else:
            logger.info("WebScraper tool disabled (playwright not installed)")
        
        # Add DatabaseSearch only if available
        if DATABASE_SEARCH_AVAILABLE:
            self.tools.append(DatabaseSearch)
            logger.info("DatabaseSearch tool enabled")
        else:
            logger.info("DatabaseSearch tool disabled (sqlalchemy not installed)")
        
        # System prompt
        self.system_prompt = """You are an advanced news trace agent. Your task is to perform DEEP TRACING of news claims, topics, or information.

CRITICAL WORKFLOW - You MUST follow these steps in MULTIPLE ITERATIONS:

PHASE 1: Initial Search
1. Use GoogleSearch to find initial sources related to the claim/topic
2. Analyze the search results to identify the most relevant URLs (at least 5-10 URLs)

PHASE 2: Deep Content Extraction (MANDATORY)
3. You MUST use WebScraper to fetch detailed content from at least 5-10 of the most relevant URLs
4. Extract full article content, not just snippets
5. Look for original sources, early reports, and authoritative sources

PHASE 3: Multi-Round Investigation
6. Based on scraped content, identify key events, dates, people, organizations
7. Use GoogleSearch again with more specific queries about:
   - Key events mentioned in scraped content
   - Dates and timelines
   - Related people/organizations
   - Original sources or early reports
8. Scrape additional URLs from these refined searches
9. Continue this process for at least 3-5 rounds to build comprehensive understanding

PHASE 4: Deep Analysis (After gathering sufficient information)
10. Analyze all collected information to:
    - Build a chronological timeline of events
    - Identify causal relationships between events
    - Extract entities (people, organizations, locations, concepts)
    - Map relationships between entities
    - Identify the original source(s) of the information

OUTPUT REQUIREMENTS:
After completing all phases, provide:
1. A comprehensive summary of findings
2. A chronological timeline of key events with dates
3. Causal relationships between events
4. A knowledge graph of entities and their relationships
5. Original source identification

Remember: This is DEEP TRACING. You must:
- Make MULTIPLE tool calls (not just one GoogleSearch)
- Scrape MANY URLs (at least 5-10, preferably more)
- Analyze content DEEPLY
- Build comprehensive understanding before summarizing"""

    async def trace_news(self, claim: str, max_iterations: int = 10, check_cancelled=None) -> TraceResult:
        """Trace the sources of a news claim with deep analysis.
        
        Args:
            claim: The news claim or article to trace
            max_iterations: Maximum number of agent iterations (increased for deep tracing)
            check_cancelled: Optional callback function that returns True if task is cancelled
            
        Returns:
            TraceResult with sources, timeline, causal relations, and knowledge graph
            
        Raises:
            asyncio.CancelledError: If task is cancelled during execution
        """
        logger.info(f"Starting DEEP news trace for claim: {claim[:100]}...")
        logger.info(f"Maximum iterations: {max_iterations}")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""Please perform DEEP TRACING for this topic/claim:

{claim}

IMPORTANT INSTRUCTIONS:
1. Start with GoogleSearch to find initial sources
2. You MUST use WebScraper to fetch detailed content from at least 5-10 URLs
3. Continue searching and scraping for multiple rounds
4. After gathering sufficient information, provide:
   - Chronological timeline of events with dates
   - Causal relationships between events
   - Knowledge graph of entities and relationships
   - Original source identification
   - Comprehensive analysis

Begin the deep tracing process now.""")
        ]
        
        # Multi-round conversation loop
        all_messages = []
        iteration = 0
        last_tool_call_count = 0
        
        try:
            logger.info(f"Starting multi-round conversation with {len(self.tools)} tools: {[t.__name__ for t in self.tools]}")
            
            while iteration < max_iterations:
                # Check if cancelled before each iteration
                if check_cancelled and check_cancelled():
                    logger.info(f"Task cancelled at iteration {iteration}")
                    raise asyncio.CancelledError("Task cancelled by user")
                
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"Iteration {iteration}/{max_iterations}")
                logger.info(f"{'='*60}")
                
                # Check if cancelled before LLM call
                if check_cancelled and check_cancelled():
                    logger.info(f"Task cancelled before LLM call at iteration {iteration}")
                    raise asyncio.CancelledError("Task cancelled by user")
                
                # Call LLM
                current_messages = await self.llm.forward(
                    messages=messages,
                    tools=self.tools,
                    response_format=None
                )
                
                # Check if cancelled after LLM call
                if check_cancelled and check_cancelled():
                    logger.info(f"Task cancelled after LLM call at iteration {iteration}")
                    raise asyncio.CancelledError("Task cancelled by user")
                
                if not current_messages or len(current_messages) == 0:
                    logger.warning(f"Iteration {iteration}: No messages returned")
                    break
                
                # Extract messages from this iteration
                iteration_messages = current_messages[0] if isinstance(current_messages[0], list) else current_messages
                
                # Count tool calls in this iteration
                tool_calls_this_iteration = sum(
                    1 for msg in iteration_messages 
                    if hasattr(msg, 'tool_calls') and msg.tool_calls
                )
                
                logger.info(f"Iteration {iteration}: {len(iteration_messages)} messages, {tool_calls_this_iteration} tool calls")
                
                # Add new messages to conversation
                messages.extend(iteration_messages)
                all_messages.extend(iteration_messages)
                
                # Check if LLM wants to continue or is done
                last_message = iteration_messages[-1] if iteration_messages else None
                if last_message:
                    last_content = getattr(last_message, 'content', '')
                    has_tool_calls = hasattr(last_message, 'tool_calls') and last_message.tool_calls
                    
                    # If no tool calls and LLM provided content, it might be done
                    if not has_tool_calls and last_content and len(last_content) > 50:
                        logger.info(f"Iteration {iteration}: LLM provided final response (no more tool calls)")
                        # But continue for a few more iterations to ensure completeness
                        if iteration >= 3 and tool_calls_this_iteration == 0:
                            logger.info("No tool calls in recent iterations, ending conversation")
                            break
                
                # Stop if no progress
                if tool_calls_this_iteration == 0 and last_tool_call_count == 0 and iteration > 2:
                    logger.info("No tool calls in consecutive iterations, ending conversation")
                    break
                
                last_tool_call_count = tool_calls_this_iteration
                
                # Check if cancelled before delay
                if check_cancelled and check_cancelled():
                    logger.info(f"Task cancelled before delay at iteration {iteration}")
                    raise asyncio.CancelledError("Task cancelled by user")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
                # Check if cancelled after delay
                if check_cancelled and check_cancelled():
                    logger.info(f"Task cancelled after delay at iteration {iteration}")
                    raise asyncio.CancelledError("Task cancelled by user")
            
            logger.info(f"\nConversation completed after {iteration} iterations")
            logger.info(f"Total messages collected: {len(all_messages)}")
            
            # Check if cancelled before analysis
            if check_cancelled and check_cancelled():
                logger.info("Task cancelled before analysis")
                raise asyncio.CancelledError("Task cancelled by user")
            
            # Extract sources from all messages
            sources = self._extract_sources_from_messages(all_messages)
            logger.info(f"Extracted {len(sources)} sources from messages")
            
            # Check if cancelled after source extraction
            if check_cancelled and check_cancelled():
                logger.info("Task cancelled after source extraction")
                raise asyncio.CancelledError("Task cancelled by user")
            
            # Perform deep analysis
            logger.info("Performing deep analysis...")
            timeline = await self._extract_timeline(all_messages, sources)
            
            # Check if cancelled after timeline extraction
            if check_cancelled and check_cancelled():
                logger.info("Task cancelled after timeline extraction")
                raise asyncio.CancelledError("Task cancelled by user")
            
            causal_relations = await self._extract_causal_relations(all_messages, sources)
            
            # Check if cancelled after causal relations extraction
            if check_cancelled and check_cancelled():
                logger.info("Task cancelled after causal relations extraction")
                raise asyncio.CancelledError("Task cancelled by user")
            
            knowledge_graph = await self._build_knowledge_graph(all_messages, sources)
            
            # Check if cancelled after knowledge graph building
            if check_cancelled and check_cancelled():
                logger.info("Task cancelled after knowledge graph building")
                raise asyncio.CancelledError("Task cancelled by user")
            
            hierarchy_graph = await self._build_hierarchy_graph(all_messages, sources, claim)
            
            # Check if cancelled after hierarchy graph building
            if check_cancelled and check_cancelled():
                logger.info("Task cancelled after hierarchy graph building")
                raise asyncio.CancelledError("Task cancelled by user")
            
            analysis = self._generate_deep_analysis(all_messages, sources, timeline, causal_relations, hierarchy_graph)
            
            logger.info(f"Analysis complete: {len(timeline)} timeline events, {len(causal_relations)} causal relations, {len(knowledge_graph.nodes) if knowledge_graph else 0} KG nodes, hierarchy depth: {hierarchy_graph.max_depth if hierarchy_graph else 0}")
            
        except asyncio.CancelledError:
            # Task was cancelled - return partial results if available
            logger.info("Task cancelled, returning partial results")
            sources = self._extract_sources_from_messages(all_messages if all_messages else messages)
            timeline = []
            causal_relations = []
            knowledge_graph = None
            try:
                hierarchy_graph = self._build_simple_hierarchy(claim, sources)
            except:
                hierarchy_graph = None
            analysis = "任务已取消，以下是已收集的部分信息。"
            # Re-raise to be handled by caller
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in agent execution: {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Fallback: try to extract from messages we have
            sources = self._extract_sources_from_messages(all_messages if all_messages else messages)
            timeline = []
            causal_relations = []
            knowledge_graph = None
            try:
                hierarchy_graph = self._build_simple_hierarchy(claim, sources)
            except:
                hierarchy_graph = None
            analysis = f"Error during analysis: {error_msg}"
        
        # Generate summary and confidence score
        summary = self._generate_summary(messages, sources)
        confidence = self._calculate_confidence(sources)
        
        result = TraceResult(
            original_claim=claim,
            sources=sources,
            confidence=confidence,
            summary=summary,
            timeline=timeline,
            causal_relations=causal_relations,
            knowledge_graph=knowledge_graph,
            hierarchy_graph=hierarchy_graph,
            analysis=analysis
        )
        
        logger.info(f"Deep trace completed: {len(sources)} sources, {len(timeline)} timeline events, confidence: {confidence:.2f}")
        return result
    
    def _extract_sources_from_messages(self, messages: List) -> List[NewsSource]:
        """Extract news sources from agent messages."""
        import json
        sources = []
        
        logger.debug(f"Extracting sources from {len(messages)} messages")
        
        for i, message in enumerate(messages):
            # Check if it's a ToolMessage
            msg_role = getattr(message, 'role', None)
            msg_type = type(message).__name__
            
            logger.debug(f"Processing message {i}: type={msg_type}, role={msg_role}")
            
            if msg_role == 'tool':
                # Extract sources from tool results
                tool_name = getattr(message, 'name', None)
                content = getattr(message, 'content', None)
                
                logger.debug(f"Found tool message: name={tool_name}, content_type={type(content).__name__}")
                
                if not tool_name or not content:
                    logger.debug(f"Skipping tool message: missing name or content")
                    continue
                
                # Handle both string and dict content
                if isinstance(content, str):
                    # Try JSON first
                    try:
                        result_data = json.loads(content)
                        logger.debug(f"Parsed JSON content for {tool_name}")
                    except (json.JSONDecodeError, TypeError):
                        # If not JSON, try to parse as dict string representation
                        try:
                            # Check if it looks like a dict string
                            if content.startswith('{') and content.endswith('}'):
                                result_data = eval(content)
                                logger.debug(f"Parsed dict string for {tool_name}")
                            else:
                                # Might be a plain string representation
                                logger.warning(f"Tool {tool_name} returned non-JSON string: {content[:100]}")
                                continue
                        except Exception as e:
                            logger.warning(f"Failed to parse content for {tool_name}: {e}")
                            continue
                elif isinstance(content, dict):
                    result_data = content
                    logger.debug(f"Content is already dict for {tool_name}")
                else:
                    logger.warning(f"Unexpected content type for {tool_name}: {type(content)}")
                    continue
                
                # Process tool results based on tool name
                if tool_name == 'GoogleSearch':
                    # Parse Google search results
                    logger.debug(f"Processing GoogleSearch results: {result_data}")
                    if result_data.get('success') and 'results' in result_data:
                        results = result_data['results']
                        logger.info(f"GoogleSearch returned {len(results)} results")
                        for idx, item in enumerate(results):
                            # Calculate relevance based on position (earlier results are more relevant)
                            # Position 1-3: 0.85-0.9, Position 4-6: 0.75-0.8, Position 7+: 0.65-0.7
                            position = item.get('position', idx + 1)
                            if position <= 3:
                                relevance = 0.9 - (position - 1) * 0.02  # 0.9, 0.88, 0.86
                            elif position <= 6:
                                relevance = 0.8 - (position - 4) * 0.02  # 0.8, 0.78, 0.76
                            else:
                                relevance = 0.7 - min((position - 7) * 0.01, 0.1)  # 0.7, 0.69, ...
                            
                            sources.append(NewsSource(
                                url=item.get('url', ''),
                                title=item.get('title', ''),
                                snippet=item.get('snippet', ''),
                                relevance_score=relevance
                            ))
                    else:
                        logger.warning(f"GoogleSearch result format unexpected: success={result_data.get('success')}, has_results={'results' in result_data}")
                
                elif tool_name == 'DatabaseSearch':
                    # Parse database search results
                    if result_data.get('success') and 'results' in result_data:
                        for idx, item in enumerate(result_data['results']):
                            # Database sources are generally more reliable, but still vary by match quality
                            # Base score 0.85-0.95 depending on position
                            position = idx + 1
                            if position <= 3:
                                relevance = 0.95 - (position - 1) * 0.03  # 0.95, 0.92, 0.89
                            else:
                                relevance = 0.88 - min((position - 4) * 0.02, 0.1)  # 0.88, 0.86, ...
                            
                            sources.append(NewsSource(
                                url=item.get('url', ''),
                                title=item.get('title', ''),
                                snippet=item.get('snippet', ''),
                                published_date=item.get('published_date'),
                                author=item.get('author'),
                                relevance_score=relevance
                            ))
                
                elif tool_name == 'WebScraper':
                    # Parse web scraper results
                    if result_data.get('success'):
                        # WebScraper sources get relevance based on content quality
                        content_length = len(result_data.get('content', ''))
                        title_length = len(result_data.get('title', ''))
                        
                        # Base relevance: 0.75-0.9 based on content quality
                        if content_length > 2000 and title_length > 10:
                            relevance = 0.9  # High quality content
                        elif content_length > 1000:
                            relevance = 0.85  # Medium quality
                        elif content_length > 500:
                            relevance = 0.8  # Lower quality
                        else:
                            relevance = 0.75  # Minimal content
                        
                        sources.append(NewsSource(
                            url=result_data.get('url', ''),
                            title=result_data.get('title', ''),
                            snippet=result_data.get('content', '')[:500] or result_data.get('meta_description', ''),
                            published_date=result_data.get('published_date'),
                            relevance_score=relevance
                        ))
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_sources = []
        for source in sources:
            if source.url and source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)
        
        return unique_sources
    
    def _generate_summary(self, messages: List, sources: List[NewsSource]) -> str:
        """Generate a summary of the trace findings."""
        if not sources:
            return "No sources found for this claim."
        
        summary_parts = [
            f"Found {len(sources)} source(s) for this claim:",
            ""
        ]
        
        for i, source in enumerate(sources[:5], 1):  # Limit to top 5
            summary_parts.append(f"{i}. {source.title}")
            if source.snippet:
                summary_parts.append(f"   {source.snippet[:200]}...")
            summary_parts.append(f"   URL: {source.url}")
            summary_parts.append("")
        
        if len(sources) > 5:
            summary_parts.append(f"... and {len(sources) - 5} more sources.")
        
        return "\n".join(summary_parts)
    
    def _calculate_confidence(self, sources: List[NewsSource]) -> float:
        """Calculate confidence score based on sources."""
        if not sources:
            return 0.0
        
        # Calculate average relevance
        relevance_scores = [s.relevance_score for s in sources if s.relevance_score is not None]
        if not relevance_scores:
            return 0.5  # Default if no relevance scores
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        
        # Base confidence on number of sources (diminishing returns)
        # 1 source: 0.3, 2-3: 0.5, 4-5: 0.6, 6-8: 0.65, 9+: 0.7
        source_count = len(sources)
        if source_count == 1:
            base_score = 0.3
        elif source_count <= 3:
            base_score = 0.3 + (source_count - 1) * 0.1  # 0.4, 0.5
        elif source_count <= 5:
            base_score = 0.5 + (source_count - 3) * 0.05  # 0.55, 0.6
        elif source_count <= 8:
            base_score = 0.6 + (source_count - 5) * 0.017  # ~0.65
        else:
            base_score = 0.7  # Cap at 0.7 for source count
        
        # Relevance contributes 30% to final confidence
        # Higher average relevance = higher confidence
        relevance_contribution = avg_relevance * 0.3
        
        # Combine: base_score (70% weight) + relevance_contribution (30% weight)
        # But we want relevance to scale the base, so:
        confidence = base_score * 0.7 + relevance_contribution
        
        # Ensure confidence is between 0.3 and 1.0
        confidence = max(0.3, min(confidence, 1.0))
        
        logger.debug(f"Confidence calculation: {len(sources)} sources, avg_relevance={avg_relevance:.2f}, base_score={base_score:.2f}, confidence={confidence:.2f}")
        
        return confidence
    
    async def _extract_timeline(self, messages: List, sources: List[NewsSource]) -> List:
        """Extract chronological timeline of events from messages and sources."""
        from app.models import TimelineEvent
        
        # Collect all content from messages
        all_content = []
        for msg in messages:
            content = getattr(msg, 'content', '')
            if content:
                all_content.append(str(content))
        
        # Also collect from sources
        for source in sources:
            if source.snippet:
                all_content.append(source.snippet)
            if source.published_date:
                all_content.append(f"Date: {source.published_date}")
        
        combined_content = "\n\n".join(all_content)
        
        # Use LLM to extract timeline with structured output
        timeline_prompt = f"""基于以下信息，提取关键事件的按时间顺序排列的时间线。

信息:
{combined_content[:5000]}

请识别关键事件及其日期和重要性。每个事件应包含：
- date: 事件日期（如果可用）
- event: 事件描述（使用中文）
- source_url: 提及该事件的URL
- importance: high（高）、medium（中）或low（低）

请确保所有事件描述使用中文。"""

        try:
            timeline_messages = [
                SystemMessage(content="你是一个时间线提取专家。从文本中提取按时间顺序排列的事件，所有描述必须使用中文。"),
                HumanMessage(content=timeline_prompt)
            ]
            
            timeline_response = await self.llm.forward(
                messages=timeline_messages,
                tools=[],
                response_format=TimelineOutput,
                max_completion_tokens=3000  # Increased for structured output
            )
            
            if timeline_response and len(timeline_response) > 0:
                response_messages = timeline_response[0] if isinstance(timeline_response[0], list) else timeline_response
                if response_messages:
                    last_msg = response_messages[-1]
                    content = getattr(last_msg, 'content', '')
                    
                    # Try to parse structured output
                    try:
                        # If content is a dict (structured output), use it directly
                        if isinstance(content, dict):
                            timeline_output = TimelineOutput(**content)
                            return timeline_output.events
                        # Otherwise, try to parse as JSON string
                        import json
                        timeline_data = json.loads(content) if isinstance(content, str) else content
                        if isinstance(timeline_data, dict) and 'events' in timeline_data:
                            timeline_output = TimelineOutput(**timeline_data)
                            return timeline_output.events
                    except Exception as e:
                        logger.warning(f"Failed to parse timeline structured output: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
        except Exception as e:
            logger.warning(f"Error extracting timeline: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        # Fallback: simple extraction from dates in sources
        timeline = []
        for source in sources:
            if source.published_date:
                timeline.append(TimelineEvent(
                    date=source.published_date,
                    event=source.title or "Event mentioned in source",
                    source_url=source.url,
                    importance="medium"
                ))
        
        return timeline
    
    async def _extract_causal_relations(self, messages: List, sources: List[NewsSource]) -> List:
        """Extract causal relationships between events."""
        from app.models import CausalRelation
        
        # Collect all content
        all_content = []
        for msg in messages:
            content = getattr(msg, 'content', '')
            if content:
                all_content.append(str(content))
        
        for source in sources:
            if source.snippet:
                all_content.append(source.snippet)
        
        combined_content = "\n\n".join(all_content)
        
        causal_prompt = f"""基于以下信息，识别事件之间的因果关系。

信息:
{combined_content[:5000]}

识别因果关系。每个关系应包含：
- cause: 原因事件（使用中文）
- effect: 结果事件（使用中文）
- relationship_type: direct（直接）、indirect（间接）或correlation（相关）
- confidence: 0.0到1.0之间的置信度
- evidence: 支持该关系的简要证据（使用中文）

请确保所有事件描述和证据使用中文。"""

        try:
            causal_messages = [
                SystemMessage(content="你是一个因果关系分析专家。识别事件之间的因果关系，所有描述必须使用中文。"),
                HumanMessage(content=causal_prompt)
            ]
            
            causal_response = await self.llm.forward(
                messages=causal_messages,
                tools=[],
                response_format=CausalRelationsOutput,
                max_completion_tokens=3000  # Increased for structured output
            )
            
            if causal_response and len(causal_response) > 0:
                response_messages = causal_response[0] if isinstance(causal_response[0], list) else causal_response
                if response_messages:
                    last_msg = response_messages[-1]
                    content = getattr(last_msg, 'content', '')
                    
                    try:
                        # If content is a dict (structured output), use it directly
                        if isinstance(content, dict):
                            causal_output = CausalRelationsOutput(**content)
                            return causal_output.relations
                        # Otherwise, try to parse as JSON string
                        import json
                        causal_data = json.loads(content) if isinstance(content, str) else content
                        if isinstance(causal_data, dict) and 'relations' in causal_data:
                            causal_output = CausalRelationsOutput(**causal_data)
                            return causal_output.relations
                    except Exception as e:
                        logger.warning(f"Failed to parse causal relations structured output: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
        except Exception as e:
            logger.warning(f"Error extracting causal relations: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return []
    
    async def _build_knowledge_graph(self, messages: List, sources: List[NewsSource]):
        """Build knowledge graph of entities and relationships."""
        from app.models import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge
        
        # Collect all content
        all_content = []
        for msg in messages:
            content = getattr(msg, 'content', '')
            if content:
                all_content.append(str(content))
        
        for source in sources:
            if source.snippet:
                all_content.append(source.snippet)
        
        combined_content = "\n\n".join(all_content)
        
        kg_prompt = f"""基于以下信息，构建实体及其关系的知识图谱。

信息:
{combined_content[:5000]}

提取:
1. 实体: 人物、组织、地点、概念、事件
2. 实体之间的关系

重要要求:
- 所有节点的label必须使用中文
- 所有边的relationship必须使用中文
- 节点类型: person（人物）、organization（组织）、location（地点）、concept（概念）、event（事件）
- 边的weight应在0.0到1.0之间"""

        try:
            kg_messages = [
                SystemMessage(content="你是一个知识图谱构建专家。提取实体和关系，所有标签和关系类型必须使用中文。"),
                HumanMessage(content=kg_prompt)
            ]
            
            kg_response = await self.llm.forward(
                messages=kg_messages,
                tools=[],
                response_format=KnowledgeGraphOutput,
                max_completion_tokens=4000  # Increased for structured output (knowledge graphs can be large)
            )
            
            if kg_response and len(kg_response) > 0:
                response_messages = kg_response[0] if isinstance(kg_response[0], list) else kg_response
                if response_messages:
                    last_msg = response_messages[-1]
                    content = getattr(last_msg, 'content', '')
                    
                    if not content:
                        logger.warning("Empty content in knowledge graph response")
                        return None
                    
                    logger.debug(f"Knowledge graph response content length: {len(str(content))}")
                    logger.debug(f"Knowledge graph response content type: {type(content)}")
                    
                    try:
                        # If content is a dict (structured output), use it directly
                        if isinstance(content, dict):
                            kg_output = KnowledgeGraphOutput(**content)
                            logger.info(f"Successfully parsed structured knowledge graph: {len(kg_output.nodes)} nodes, {len(kg_output.edges)} edges")
                            return KnowledgeGraph(nodes=kg_output.nodes, edges=kg_output.edges)
                        
                        # Otherwise, try to parse as JSON string
                        import json
                        kg_data = json.loads(content) if isinstance(content, str) else content
                        if isinstance(kg_data, dict):
                            # Check if it has the expected structure
                            if 'nodes' in kg_data and 'edges' in kg_data:
                                kg_output = KnowledgeGraphOutput(**kg_data)
                                logger.info(f"Successfully parsed knowledge graph from JSON: {len(kg_output.nodes)} nodes, {len(kg_output.edges)} edges")
                                return KnowledgeGraph(nodes=kg_output.nodes, edges=kg_output.edges)
                            else:
                                logger.warning(f"Knowledge graph data missing 'nodes' or 'edges': {list(kg_data.keys())}")
                    except Exception as e:
                        logger.warning(f"Failed to parse knowledge graph structured output: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
        except Exception as e:
            logger.warning(f"Error building knowledge graph: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return None
    
    def _try_fix_incomplete_json(self, json_str: str):
        """尝试修复不完整的JSON字符串。
        
        Args:
            json_str: 可能不完整的JSON字符串
            
        Returns:
            解析后的字典，如果无法修复则返回None
        """
        try:
            # 尝试补全缺失的括号
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')
            
            # 补全缺失的括号
            if open_braces > close_braces:
                json_str += '}' * (open_braces - close_braces)
            if open_brackets > close_brackets:
                json_str += ']' * (open_brackets - close_brackets)
            
            # 尝试移除末尾不完整的字符串
            # 如果最后有未闭合的引号，尝试修复
            if json_str.rstrip().endswith('"') and json_str.count('"') % 2 != 0:
                # 移除最后一个不完整的字符串
                last_quote = json_str.rfind('"')
                if last_quote > 0:
                    # 检查是否在字符串中间
                    before_quote = json_str[:last_quote]
                    if before_quote.count('"') % 2 == 0:
                        # 在字符串中间，尝试闭合
                        json_str = json_str[:last_quote] + '"'
            
            # 尝试移除末尾不完整的对象或数组
            json_str = json_str.rstrip()
            if json_str.endswith(','):
                json_str = json_str[:-1]
            
            # 尝试解析修复后的JSON
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 如果还是失败，尝试提取部分数据
                # 提取nodes数组
                nodes_match = re.search(r'"nodes"\s*:\s*\[([\s\S]*?)(?:\]|$)', json_str)
                edges_match = re.search(r'"edges"\s*:\s*\[([\s\S]*?)(?:\]|$)', json_str)
                
                nodes = []
                edges = []
                
                if nodes_match:
                    nodes_str = nodes_match.group(1)
                    # 尝试提取每个节点对象
                    node_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    for node_match in re.finditer(node_pattern, nodes_str):
                        try:
                            node_obj = json.loads(node_match.group())
                            nodes.append(node_obj)
                        except:
                            continue
                
                if edges_match:
                    edges_str = edges_match.group(1)
                    # 尝试提取每条边对象
                    edge_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    for edge_match in re.finditer(edge_pattern, edges_str):
                        try:
                            edge_obj = json.loads(edge_match.group())
                            edges.append(edge_obj)
                        except:
                            continue
                
                if nodes or edges:
                    logger.info(f"Partially recovered knowledge graph: {len(nodes)} nodes, {len(edges)} edges")
                    return {'nodes': nodes, 'edges': edges}
                
        except Exception as e:
            logger.debug(f"Failed to fix incomplete JSON: {e}")
        
        return None
    
    async def _build_hierarchy_graph(self, messages: List, sources: List[NewsSource], original_claim: str):
        """Build hierarchical graph showing trace depth and structure."""
        from app.models import HierarchyGraph, HierarchyNode
        import json
        import re
        
        # Collect all content and tool call information
        all_content = []
        tool_call_sequence = []  # Track tool calls in order
        
        for msg in messages:
            msg_role = getattr(msg, 'role', None)
            content = getattr(msg, 'content', '')
            
            # Track tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = getattr(tool_call.function, 'name', '') if hasattr(tool_call, 'function') else ''
                    tool_call_sequence.append({
                        'tool': tool_name,
                        'content': content
                    })
            
            # Track tool results
            if msg_role == 'tool':
                tool_name = getattr(msg, 'name', '')
                if content:
                    all_content.append(f"[{tool_name}]: {str(content)[:500]}")
        
        # Also collect from sources
        for source in sources:
            if source.snippet:
                all_content.append(f"[Source]: {source.title} - {source.snippet[:200]}")
        
        combined_content = "\n\n".join(all_content)
        
        # Use LLM to analyze hierarchy structure
        hierarchy_prompt = f"""基于以下新闻溯源信息，构建一个展示溯源深度的层次结构。

原始声明: {original_claim}

溯源信息:
{combined_content[:8000]}

分析溯源深度并构建层次结构:
- Level 0 (根节点): 原始声明/主题
- Level 1: 初始搜索结果和主要来源
- Level 2: 从主要来源提取的关键信息（主要观点、事实、事件）
- Level 3: 更深入的分析、相关概念或次要信息
- Level 4+: 更详细的信息或子主题

返回以下结构的JSON:
{{
  "root_id": "root",
  "nodes": [
    {{
      "id": "node_id",
      "label": "节点名称（必须使用中文）",
      "level": 0-4,
      "parent_id": "父节点id或null（根节点为null）",
      "source_urls": ["url1", "url2"],
      "description": "简要描述（必须使用中文）",
      "source_count": 2
    }}
  ],
  "max_depth": 3
}}

规则:
1. 根节点（level 0）应代表原始声明
2. Level 1 节点应为主要来源或搜索结果类别
3. Level 2+ 节点应代表从来源中提取的更深层信息
4. 每个节点应有适当的parent_id以形成树形结构
5. 包含支持每个节点的来源URL
6. max_depth应为层次结构中的最高层级
7. **重要：所有节点的label和description必须使用中文**

只返回有效的JSON，不要其他文本。"""

        try:
            hierarchy_messages = [
                SystemMessage(content="你是一个层次结构分析专家。根据新闻来源构建展示溯源深度的层次结构。所有节点标签和描述必须使用中文。返回JSON格式。"),
                HumanMessage(content=hierarchy_prompt)
            ]
            
            hierarchy_response = await self.llm.forward(
                messages=hierarchy_messages,
                tools=[],
                response_format=HierarchyGraphOutput,
                max_completion_tokens=4000  # Increased for structured output
            )
            
            if hierarchy_response and len(hierarchy_response) > 0:
                response_messages = hierarchy_response[0] if isinstance(hierarchy_response[0], list) else hierarchy_response
                if response_messages:
                    last_msg = response_messages[-1]
                    content = getattr(last_msg, 'content', '')
                    
                    try:
                        # If content is a dict (structured output), use it directly
                        if isinstance(content, dict):
                            hierarchy_output = HierarchyGraphOutput(**content)
                            # Calculate children count for each node
                            for node in hierarchy_output.nodes:
                                node.children_count = sum(1 for n in hierarchy_output.nodes if n.parent_id == node.id)
                            logger.info(f"Successfully parsed structured hierarchy graph: {len(hierarchy_output.nodes)} nodes, max_depth={hierarchy_output.max_depth}")
                            return HierarchyGraph(
                                root_id=hierarchy_output.root_id,
                                nodes=hierarchy_output.nodes,
                                max_depth=hierarchy_output.max_depth
                            )
                        
                        # Otherwise, try to parse as JSON string
                        import json
                        hierarchy_data = json.loads(content) if isinstance(content, str) else content
                        if isinstance(hierarchy_data, dict):
                            hierarchy_output = HierarchyGraphOutput(**hierarchy_data)
                            # Calculate children count for each node
                            for node in hierarchy_output.nodes:
                                node.children_count = sum(1 for n in hierarchy_output.nodes if n.parent_id == node.id)
                            logger.info(f"Successfully parsed hierarchy graph from JSON: {len(hierarchy_output.nodes)} nodes, max_depth={hierarchy_output.max_depth}")
                            return HierarchyGraph(
                                root_id=hierarchy_output.root_id,
                                nodes=hierarchy_output.nodes,
                                max_depth=hierarchy_output.max_depth
                            )
                    except Exception as e:
                        logger.warning(f"Failed to parse hierarchy structured output: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
        except Exception as e:
            logger.warning(f"Error building hierarchy graph: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        # Fallback: Build simple hierarchy from sources
        return self._build_simple_hierarchy(original_claim, sources)
    
    def _build_simple_hierarchy(self, original_claim: str, sources: List[NewsSource]):
        """Build a simple hierarchy from sources as fallback."""
        from app.models import HierarchyGraph, HierarchyNode
        
        nodes = []
        
        # Root node
        root_id = "root"
        nodes.append(HierarchyNode(
            id=root_id,
            label=original_claim[:100],
            level=0,
            parent_id=None,
            source_urls=[],
            description="原始声明",
            source_count=0,
            children_count=len(sources)
        ))
        
        # Level 1: Group sources by domain or category
        source_groups = {}
        for i, source in enumerate(sources):
            # Extract domain from URL
            try:
                from urllib.parse import urlparse
                domain = urlparse(source.url).netloc
                if domain not in source_groups:
                    source_groups[domain] = []
                source_groups[domain].append(source)
            except:
                # Fallback: use index
                source_groups[f"group_{i}"] = [source]
        
        # Create level 1 nodes for each group
        level1_nodes = []
        for group_id, group_sources in list(source_groups.items())[:10]:  # Limit to 10 groups
            node_id = f"level1_{group_id}"
            level1_nodes.append(node_id)
            nodes.append(HierarchyNode(
                id=node_id,
                label=f"来源组: {group_id}",
                level=1,
                parent_id=root_id,
                source_urls=[s.url for s in group_sources],
                description=f"包含 {len(group_sources)} 个来源",
                source_count=len(group_sources),
                children_count=0
            ))
        
        # Update root children count
        if nodes:
            nodes[0].children_count = len(level1_nodes)
        
        max_depth = 1 if level1_nodes else 0
        
        return HierarchyGraph(
            root_id=root_id,
            nodes=nodes,
            max_depth=max_depth
        )
    
    def _generate_deep_analysis(self, messages: List, sources: List[NewsSource], timeline: List, causal_relations: List, hierarchy_graph) -> str:
        """Generate deep analysis of trace findings."""
        analysis_parts = [
            "=== 深度溯源分析 ===\n",
            f"共收集 {len(sources)} 个来源",
            f"识别 {len(timeline)} 个时间线事件",
            f"发现 {len(causal_relations)} 个因果关系",
            f"溯源深度: {hierarchy_graph.max_depth if hierarchy_graph else 0} 层\n" if hierarchy_graph else "",
        ]
        
        if timeline:
            analysis_parts.append("=== 时间线 ===")
            for event in sorted(timeline, key=lambda x: x.date or ""):
                date_str = event.date or "日期未知"
                analysis_parts.append(f"{date_str}: {event.event} (重要性: {event.importance})")
            analysis_parts.append("")
        
        if causal_relations:
            analysis_parts.append("=== 因果关系 ===")
            for rel in causal_relations:
                analysis_parts.append(f"原因: {rel.cause}")
                analysis_parts.append(f"结果: {rel.effect}")
                analysis_parts.append(f"关系类型: {rel.relationship_type}, 置信度: {rel.confidence:.2f}")
                if rel.evidence:
                    analysis_parts.append(f"证据: {rel.evidence}")
                analysis_parts.append("")
        
        return "\n".join(analysis_parts)

