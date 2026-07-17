# CareerCraft Agent — Sprint 4-6 WebView + Remaining Backend

## Context
- Project: /mnt/d/workplace_for_hermes/career-agent/
- Python 3.11, PySide6, QWebEngineView, QWebChannel
- All PEP 585 built-in generics banned; use typing.List/Dict/Optional/etc
- No real API keys; mock mode only
- Existing services: experience_manager, persona_engine, resume_builder, job_matcher, job_parser, learning_recommender, retelling_engine
- Existing ORM: 7 tables in SQLite via SQLAlchemy async
- HTML prototype: /prototype/ui-prototype.html (34KB, 6 pages, Linear dark style)

## Task A: WebView Framework
Create src/ui/webview/ module:

1. **src/ui/webview/__init__.py** — exports
2. **src/ui/webview/bridge.py** — QWebChannel Python object:
   - Class `CareerBridge(QObject)` with `@pyqtSlot` methods:
     - `getExperiences()` -> JSON string
     - `getPersonas()` -> JSON string
     - `saveExperience(data: str)` -> JSON string
     - `generateResume(personaId: str)` -> JSON string
     - `matchJob(jdText: str)` -> JSON string
     - `getLearningPath(skill: str)` -> JSON string
     - `getStats()` -> JSON string (for welcome page)
   - All methods use existing services from src/services/ (mock mode, no real LLM)
   - Return JSON strings for easy JS parsing
3. **src/ui/webview/webview_window.py** — Main window:
   - `CareerWebWindow(QMainWindow)`
   - Central widget: QWebEngineView
   - Load file:///prototype/ui-prototype.html
   - Inject QWebChannel with CareerBridge instance
   - Window title: "CareerCraft Agent", size 1280x800, dark frameless or native frame
   - Enable DevTools with F12 (QWebEnginePage::InspectElement)
4. **src/ui/webview/api_handler.py** — (optional adapter) maps bridge calls to async services using asyncio.run_coroutine_threadsafe if needed

## Task B: HTML Prototype Bridge Wiring
Modify /prototype/ui-prototype.html:
- Add qwebchannel.js (from PySide6/PyQt5 webchannel) or inline the minimal bridge script
- Add JS `window.pybridge` that calls `new QWebChannel(qt.webChannelTransport, ...)`
- Wire all interactive buttons to call `window.pybridge.*` methods:
  - Welcome page stats load from `getStats()`
  - Experience list loads from `getExperiences()`
  - "+ 新建" calls `saveExperience()`
  - Resume preview calls `generateResume()`
  - Job match calls `matchJob()`
- Keep all fallback mock data so page works standalone in browser too

## Task C: Entry Point
Modify src/main.py or create src/main_webview.py:
- New entry point that launches CareerWebWindow
- Keep old QWidget main_window entry point intact (backward compat)
- `python -m src.main_webview` launches the WebView version

## Task D: Remaining Backend (Sprint 4-6)
1. **src/llm/router.py** — multi-model fallback:
   - If primary model fails, try secondary model
   - If all fail, return structured mock response based on prompt keywords
   - Add retry decorator (3 attempts, exponential backoff)
2. **src/services/pdf_exporter.py** — PDF export:
   - Use fpdf2 (already in requirements)
   - Convert markdown resume to PDF with basic styling
   - Method: `export_pdf(markdown_text: str, output_path: str)`
3. **src/crawlers/jd_crawler.py** — Stub JD crawler:
   - Use playwright stub (no real crawling without API key)
   - Mock method: `fetch_jd(url: str) -> str` returns sample JD text
4. **src/ui/webview/devtools.py** — Optional dev helper enabling remote debugging port

## Rules
- NO PEP 585: use List, Dict, Optional from typing
- All Chinese text in source must be UTF-8 literal, NO \uXXXX escapes
- No real API keys or live LLM calls
- Add type hints everywhere
- Create/update tests for new modules
- Update INDEX.md with progress

## Codex Command
Run the above tasks. Create files incrementally, verify imports after each module.
