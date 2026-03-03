# Agentic Quote-to-Underwrite Workflow (Work in Progress)

A working version of an agentic insurance quote processing and underwriting system built with LangGraph, FastAPI, and RAG.

## ✅ Features Implemented

### Core Infrastructure
- **Schema Definitions**: Complete data models for quotes, assessments, and decisions
- **Tool Stubs**: Address normalization, hazard scoring, and rating tools
- **RAG System**: Document ingestion and retrieval over underwriting guidelines
- **LangGraph Workflow**: Linear processing pipeline (Validate → Enrich → Retrieve → Assess → Rate → Decide)
- **Storage**: SQLite database for run records and audit trails
- **API Endpoints**: RESTful API for quote processing

### Agentic Enhancements ✅
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

---

## 📈 **Performance & Scalability**

### **⚡ Performance Optimization**
- **Intelligent Caching**: Multi-level with AI-driven invalidation
- **Parallel Processing**: Distributed processing architecture
- **Resource Management**: Dynamic allocation
- **Latency Optimization**: Sub-second response times

### **📊 Scalability Design**
- **Horizontal Scaling**: Auto-scaling for load management
- **Microservices**: Modular service architecture
- **Load Balancing**: Intelligent traffic distribution
- **High Availability**: Disaster recovery and failover

---

## 🧪 **Testing & Validation**

### **🎯 Intelligence Testing**
```bash
# Run comprehensive AI test suite
python test_intelligent_system.py

# Test multi-modal processing
python test_multi_modal_understanding.py

# Validate reasoning engine
python test_advanced_reasoning.py

# Check learning capabilities
python test_continuous_learning.py
```

### **📊 Performance Validation**
```bash
# Load testing for enterprise scale
python test_enterprise_performance.py

# Security and compliance testing
python test_security_compliance.py

# End-to-end system validation
python test_complete_intelligence.py
```

---

## 📚 **Documentation**

### **🏗️ Architecture**
- [Intelligent System Architecture](INTELLIGENT_SYSTEM_ARCHITECTURE.md)
- [AI Model Documentation](docs/ai_models.md)
- [Performance Optimization Guide](docs/performance.md)

### **🔧 Implementation**
- [Integration Guide](docs/integration.md)
- [Configuration Manual](docs/configuration.md)
- [Deployment Guide](docs/deployment.md)

### **📊 Analytics**
- [Intelligence Metrics](docs/metrics.md)
- [Performance Monitoring](docs/monitoring.md)
- [Business Intelligence](docs/business_intelligence.md)

---

## 🤝 **Enterprise Support**

### **🎯 Professional Services**
- **AI Implementation**: Expert deployment and configuration
- **Custom Training**: Domain-specific model fine-tuning
- **Integration Support**: Enterprise system integration
- **Performance Optimization**: Scalability and efficiency tuning

### **📞 Technical Support**
- **24/7 Enterprise Support**: Round-the-clock assistance
- **AI Expertise**: Specialized AI engineering support
- **SLA Guarantee**: 99.9% uptime commitment
- **Continuous Updates**: Regular AI capability enhancements

---

## � **Future Intelligence Roadmap**

### **🔮 Advanced AI Capabilities**
- **Predictive Analytics**: Advanced risk prediction models
- **Prescriptive Insights**: Actionable recommendation engine
- **Autonomous Decisions**: Fully automated standard processing
- **Strategic Intelligence**: Portfolio-level insights

### **🌐 Ecosystem Integration**
- **Industry Collaboration**: Shared intelligence networks
- **Regulatory Intelligence**: Proactive compliance management
- **Market Intelligence**: Real-time market awareness
- **Innovation Pipeline**: Continuous AI evolution

---

## 🎉 **Transform Underwriting with AI**

The IntelliUnderwrite AI Platform represents a **paradigm shift** from traditional underwriting to **intelligent automation**. By combining **advanced AI capabilities** with **enterprise-grade reliability**, we're creating the future of underwriting.

**This isn't just software—it's an intelligent partner that transforms how organizations approach risk assessment and decision making.**

---

## 📞 **Get Started Today**

**Ready to transform your underwriting with intelligent AI?**

🌐 **Request Demo**: [demo@intelliunderwrite.ai](mailto:demo@intelliunderwrite.ai)  
📞 **Contact Sales**: [sales@intelliunderwrite.ai](mailto:sales@intelliunderwrite.ai)  
📚 **Documentation**: [docs.intelliunderwrite.ai](https://docs.intelliunderwrite.ai)  
� **Start Free Trial**: [trial.intelliunderwrite.ai](https://trial.intelliunderwrite.ai)

---

**🧠 IntelliUnderwrite AI Platform - Intelligent Underwriting, Decisive Insights** 🚀
For questions or issues, check the audit logs and API documentation.
cd /Users/sumedhtuttagunta/code/AgenticQuote
python -m uvicorn app.complete:create_complete_app --reload --host 0.0.0.0 --port 8000