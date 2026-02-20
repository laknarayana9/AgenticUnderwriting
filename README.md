# Agentic Quote-to-Underwrite Workflow

A 2-day working version of an agentic insurance quote processing and underwriting system built with LangGraph, FastAPI, and RAG.

## ✅ Features Implemented

### Day 1 - Core Infrastructure
- **Schema Definitions**: Complete data models for quotes, assessments, and decisions
- **Tool Stubs**: Address normalization, hazard scoring, and rating tools
- **RAG System**: Document ingestion and retrieval over underwriting guidelines
- **LangGraph Workflow**: Linear processing pipeline (Validate → Enrich → Retrieve → Assess → Rate → Decide)
- **Storage**: SQLite database for run records and audit trails
- **API Endpoints**: RESTful API for quote processing

### Day 2 - Agentic Enhancements ✅
- **Missing-info Loop**: Agentic behavior for handling incomplete submissions
- **Strict Citation Guardrail**: Forces REFER when assessment lacks proper citations
- **Simple UI**: Demo interface for testing and visualization
- **Enhanced Audit Trail**: Complete tool call traceability and run history

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   LangGraph      │    │   Storage       │
│   Endpoints     │───▶│   Workflow       │───▶│   SQLite DB     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   RAG Engine     │
                       │   (ChromaDB)     │
                       └──────────────────┘
```

## 🚀 Quick Start

### 1. Automated Setup

```bash
# Clone and navigate to the project
cd AgenticQuote

# Run the setup script
python setup.py
```

The setup script will:
- Install all dependencies
- Create necessary directories
- Initialize the RAG system with guideline documents
- Test the workflow

### 2. Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p storage storage/chroma_db

# Initialize RAG (optional - done automatically on first run)
python -c "from app.rag_engine import RAGEngine; RAGEngine().ingest_documents()"
```

### 3. Run the Application

```bash
# Start the API server
python -m app.main
```

The API will be available at `http://localhost:8000`

### 4. Access the UI

Open your browser to: `http://localhost:8000/static/index.html`

## 🧪 Testing

### Automated Testing
```bash
# Run the test script
python test_api.py
```

### Manual Testing with curl
```bash
# Submit a quote for processing
curl -X POST "http://localhost:8000/quote/run" \
  -H "Content-Type: application/json" \
  -d '{
    "submission": {
      "applicant_name": "John Doe",
      "address": "123 Main St, Los Angeles, CA 90210",
      "property_type": "single_family",
      "coverage_amount": 500000,
      "construction_year": 1985,
      "square_footage": 2000,
      "roof_type": "asphalt_shingle",
      "foundation_type": "concrete"
    },
    "use_agentic": true
  }'
```

## 📚 API Documentation

### Core Endpoints

#### Processing
- `POST /quote/run` - Process a quote submission
  - `use_agentic: true` enables missing-info loops and citation guardrails
- `GET /runs/{run_id}` - Get run status and results
- `GET /runs/{run_id}/audit` - Get full audit trail with tool calls

#### Management
- `GET /runs` - List recent runs
- `GET /stats` - Get system statistics
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

## 🔄 Workflow Nodes

1. **Validate**: Check submission completeness and basic requirements
2. **Enrich**: Normalize address and calculate hazard scores
3. **RetrieveGuidelines**: Fetch relevant underwriting guidelines via RAG
4. **UWAssess**: Perform underwriting assessment with citations
5. **CitationGuardrail**: Ensure decisions have proper evidence
6. **Rate**: Calculate insurance premium
7. **Decide**: Make final decision (Accept/Refer/Decline)
8. **HandleMissingInfo**: Agentic loop for incomplete submissions
9. **StoreRun**: Persist results for audit trail

## 📊 Data Models

### Core Entities
- `QuoteSubmission`: Input quote data
- `EnrichmentResult`: Normalized address + hazard scores
- `RetrievalChunk`: RAG-retrieved guideline text
- `UWAssessment`: Underwriting evaluation with triggers
- `Decision`: Final underwriting decision
- `RunRecord`: Complete audit trail

### Decision Types
- **ACCEPT**: Policy can be issued
- **REFER**: Requires manual underwriter review
- **DECLINE**: Not eligible for coverage

## 🧠 RAG System

Uses hybrid retrieval with:
- **Embeddings**: Sentence transformers for semantic search
- **Vector DB**: ChromaDB for storage
- **Documents**: 5 underwriting guideline files
  - Wildfire Risk Assessment
  - Flood Risk Assessment  
  - Property Eligibility
  - Construction Standards
  - Underwriting Workflow
- **Citations**: Full traceability to source documents

## 🛠️ Tools

### AddressNormalizeTool
- Parses and standardizes addresses
- Mock implementation (production: use geocoding API)

### HazardScoreTool  
- Calculates wildfire, flood, wind, earthquake risks
- County-based risk scoring (mock data)

### RatingTool
- Calculates insurance premiums
- Factors in property type, hazards, construction age

## 💾 Storage

- **Database**: SQLite
- **Schema**: Run records with full state preservation
- **Audit**: Complete tool call traceability
- **Retention**: All runs stored for analysis

## 🤖 Agentic Features

### Missing-Info Loop
- Detects incomplete submissions
- Generates specific questions for missing data
- Processes answers and re-runs workflow
- Maintains conversation context

### Citation Guardrail
- Validates that underwriting decisions have evidence
- Forces REFER if citations are missing
- Ensures auditability and compliance

## 📁 Project Structure
```
├── app/                 # FastAPI application
│   ├── main.py         # API endpoints
│   └── rag_engine.py   # RAG implementation
├── models/             # Pydantic schemas
├── tools/              # Underwriting tools
├── workflows/          # LangGraph workflow
│   ├── nodes.py        # Workflow nodes
│   ├── graph.py        # Linear workflow
│   └── agentic_graph.py # Enhanced workflow
├── storage/            # Database layer
├── data/               # Sample guidelines
├── static/             # Web UI
└── storage/            # ChromaDB + SQLite
```

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key_here  # For enhanced LLM features
DATABASE_URL=sqlite:///./underwriting.db   # Database connection
```

## 📈 System Statistics

The system tracks:
- Total runs processed
- Runs by status (completed/failed)
- Recent activity (last 24 hours)
- Decision distribution

## 🚦 Production Considerations

- Replace mock tools with real APIs (geocoding, hazard data, rating engine)
- Add authentication/authorization
- Implement proper logging/monitoring
- Add comprehensive error handling
- Scale RAG with better chunking strategies
- Add evaluation harness for accuracy metrics
- Implement proper secrets management

## 🎯 Demo Scenarios

Try these test cases in the UI:

1. **Low Risk Property**: New construction, low hazard area → Should ACCEPT
2. **High Wildfire Risk**: Old construction in wildfire zone → Should REFER
3. **Missing Info**: Incomplete submission → Should request more info
4. **Commercial Property**: Non-eligible property type → Should DECLINE

## 🔍 Debugging

- Check API logs for detailed error information
- Use `/runs/{id}/audit` to see full workflow execution
- Monitor tool calls and citations in the audit trail
- Verify RAG document ingestion in setup logs

## 📞 Support

This is a 2-day proof-of-concept demonstrating:
- ✅ Principal-style architecture thinking
- ✅ Agentic workflow orchestration
- ✅ RAG-powered decision support
- ✅ Audit-ready underwriting system
- ✅ Working MVP with UI and API

For questions or issues, check the audit logs and API documentation.
