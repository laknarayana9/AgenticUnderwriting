/**
 * Evidence-First Underwriting UI
 * Three-panel interface for evidence visualization and decision making
 */

class EvidenceUI {
    constructor() {
        this.currentEvidence = [];
        this.currentDecision = null;
        this.selectedChunk = null;
        this.ragEngine = null;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Evidence item clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.evidence-item')) {
                this.selectEvidenceItem(e.target.closest('.evidence-item'));
            }
            
            if (e.target.classList.contains('citation-tag')) {
                this.jumpToCitation(e.target.dataset.citationId);
            }
        });
    }
    
    /**
     * Display evidence in three-panel UI
     */
    async displayEvidence(submissionData, decisionResult) {
        console.log('🎯 Displaying evidence for decision:', decisionResult);
        
        // Handle different data structures
        let decision, evidence, requiredQuestions, referralTriggers, conditions, citations;
        
        if (decisionResult.decision) {
            // Full decision object structure
            decision = decisionResult.decision;
            evidence = decisionResult.evidence || [];
            requiredQuestions = decisionResult.required_questions || [];
            referralTriggers = decisionResult.referral_triggers || [];
            conditions = decisionResult.conditions || [];
            citations = decisionResult.citations || [];
        } else {
            // Flat structure (fallback)
            decision = decisionResult;
            evidence = decisionResult.evidence || [];
            requiredQuestions = decisionResult.required_questions || [];
            referralTriggers = decisionResult.referral_triggers || [];
            conditions = decisionResult.conditions || [];
            citations = decisionResult.citations || [];
        }
        
        this.currentDecision = decision;
        this.currentEvidence = evidence;
        
        // Update decision panel
        this.updateDecisionPanel(decision);
        
        // Update evidence trace panel
        this.updateEvidencePanel(evidence);
        
        // Update source document panel
        await this.updateDocumentPanel(evidence);
        
        // Show the evidence container
        this.showEvidenceContainer();
    }
    
    /**
     * Update decision panel with decision information
     */
    updateDecisionPanel(decision) {
        console.log('📊 Updating decision panel with:', decision);
        
        // Handle case where decision might be null/undefined
        if (!decision) {
            console.error('❌ Decision object is null or undefined');
            return;
        }
        
        const decisionType = decision.decision || 'REFER';
        const confidence = decision.confidence || 0.0;
        const reason = decision.reason || 'Underwriting decision based on evidence review';
        
        console.log('🔍 Decision data:', { decisionType, confidence, reason });
        
        // Update decision type
        const decisionElement = document.querySelector('.decision-type');
        if (decisionElement) {
            decisionElement.textContent = decisionType.toUpperCase();
            decisionElement.className = `decision-type ${decisionType.toLowerCase()}`;
        }
        
        // Update confidence indicator
        this.updateConfidenceIndicator(confidence);
        
        // Update decision reason
        const reasonElement = document.querySelector('.decision-reason');
        if (reasonElement) {
            reasonElement.textContent = reason;
        }
        
        // Update required questions
        this.updateRequiredQuestions(decision.required_questions || []);
        
        // Update referral triggers
        this.updateReferralTriggers(decision.referral_triggers || []);
        
        // Update conditions
        this.updateConditions(decision.conditions || []);
    }
    
    /**
     * Update confidence indicator
     */
    updateConfidenceIndicator(confidence) {
        const confidenceFill = document.querySelector('.confidence-fill');
        const confidenceText = document.querySelector('.confidence-text');
        
        if (confidenceFill) {
            confidenceFill.style.width = `${confidence * 100}%`;
            
            // Update color based on confidence level
            confidenceFill.className = 'confidence-fill';
            if (confidence >= 0.8) {
                confidenceFill.classList.add('high');
            } else if (confidence >= 0.6) {
                confidenceFill.classList.add('medium');
            } else {
                confidenceFill.classList.add('low');
            }
        }
        
        if (confidenceText) {
            confidenceText.textContent = `${Math.round(confidence * 100)}% confidence`;
        }
    }
    
    /**
     * Update required questions section
     */
    updateRequiredQuestions(questions) {
        const questionsContainer = document.querySelector('.required-questions');
        if (!questionsContainer) return;
        
        if (questions.length === 0) {
            questionsContainer.innerHTML = '<p class="text-gray-500">No additional information required</p>';
            return;
        }
        
        const questionsHTML = questions.map(q => `
            <div class="question-item">
                <div class="question-priority priority-${q.priority || 'P2'}">
                    ${q.priority || 'P2'} Priority
                </div>
                <div class="question-text">${q.question}</div>
                ${q.source ? `<div class="question-source">Source: ${q.source}</div>` : ''}
            </div>
        `).join('');
        
        questionsContainer.innerHTML = questionsHTML;
    }
    
    /**
     * Update referral triggers section
     */
    updateReferralTriggers(triggers) {
        const triggersContainer = document.querySelector('.referral-triggers');
        if (!triggersContainer) return;
        
        if (triggers.length === 0) {
            triggersContainer.innerHTML = '<p class="text-gray-500">No referral triggers</p>';
            return;
        }
        
        const triggersHTML = triggers.map(trigger => `
            <div class="trigger-item">
                <div class="trigger-text">• ${trigger}</div>
            </div>
        `).join('');
        
        triggersContainer.innerHTML = triggersHTML;
    }
    
    /**
     * Update conditions section
     */
    updateConditions(conditions) {
        const conditionsContainer = document.querySelector('.decision-conditions');
        if (!conditionsContainer) return;
        
        if (conditions.length === 0) {
            conditionsContainer.innerHTML = '<p class="text-gray-500">No special conditions</p>';
            return;
        }
        
        const conditionsHTML = conditions.map(condition => `
            <div class="condition-item">
                <div class="condition-text">• ${condition}</div>
            </div>
        `).join('');
        
        conditionsContainer.innerHTML = conditionsHTML;
    }
    
    /**
     * Update evidence trace panel
     */
    updateEvidencePanel(evidence) {
        const evidenceContainer = document.querySelector('.evidence-list');
        if (!evidenceContainer) return;
        
        if (evidence.length === 0) {
            evidenceContainer.innerHTML = '<p class="text-gray-500">No evidence retrieved</p>';
            return;
        }
        
        const evidenceHTML = evidence.map((chunk, index) => `
            <div class="evidence-item fade-in" data-chunk-id="${chunk.chunk_id}" data-index="${index}">
                <div class="evidence-header">
                    <div class="evidence-source">${chunk.doc_title || 'Unknown Document'}</div>
                    <div class="evidence-relevance">Relevance: ${Math.round((chunk.relevance_score || 0) * 100)}%</div>
                </div>
                <div class="evidence-text">${this.truncateText(chunk.text, 200)}</div>
                <div class="evidence-meta">
                    <div class="rule-strength-badge ${chunk.metadata?.rule_strength || 'informational'}">
                        ${chunk.metadata?.rule_strength || 'informational'}
                    </div>
                    <div class="evidence-section">${chunk.section || 'Unknown Section'}</div>
                    <div class="citation-tag" data-citation-id="${chunk.chunk_id}">G${index + 1}</div>
                </div>
            </div>
        `).join('');
        
        evidenceContainer.innerHTML = evidenceHTML;
    }
    
    /**
     * Update source document panel with highlighted evidence
     */
    async updateDocumentPanel(evidence) {
        const documentContainer = document.querySelector('.document-viewer');
        if (!documentContainer) return;
        
        if (evidence.length === 0) {
            documentContainer.innerHTML = '<p class="text-gray-500">No source documents available</p>';
            return;
        }
        
        // Group evidence by document
        const documentsBySource = {};
        evidence.forEach(chunk => {
            const source = chunk.doc_title || 'Unknown Document';
            if (!documentsBySource[source]) {
                documentsBySource[source] = [];
            }
            documentsBySource[source].push(chunk);
        });
        
        // Generate document HTML
        const documentHTML = Object.entries(documentsBySource).map(([source, chunks]) => `
            <div class="document-section">
                <h3>${source}</h3>
                ${chunks.map(chunk => this.highlightEvidence(chunk)).join('')}
            </div>
        `).join('');
        
        documentContainer.innerHTML = documentHTML;
    }
    
    /**
     * Highlight evidence text based on rule strength
     */
    highlightEvidence(chunk) {
        const ruleStrength = chunk.metadata?.rule_strength || 'informational';
        const highlightClass = `highlight-${ruleStrength}`;
        
        return `
            <div class="${highlightClass}" data-chunk-id="${chunk.chunk_id}">
                <div class="evidence-content">
                    ${chunk.text}
                    <div class="citation-tag" data-citation-id="${chunk.chunk_id}">View Evidence</div>
                </div>
            </div>
        `;
    }
    
    /**
     * Select evidence item and show details
     */
    selectEvidenceItem(element) {
        // Remove previous selection
        document.querySelectorAll('.evidence-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add selection to clicked item
        element.classList.add('active');
        
        // Get chunk data
        const chunkId = element.dataset.chunkId;
        const index = parseInt(element.dataset.index);
        const chunk = this.currentEvidence[index];
        
        if (chunk) {
            this.selectedChunk = chunk;
            this.showEvidenceDetails(chunk);
            
            // Scroll to corresponding highlight in document panel
            this.scrollToHighlight(chunkId);
        }
    }
    
    /**
     * Show detailed evidence information
     */
    showEvidenceDetails(chunk) {
        // This could show a modal or side panel with full details
        console.log('📋 Evidence Details:', {
            chunk_id: chunk.chunk_id,
            source: chunk.doc_title,
            section: chunk.section,
            rule_strength: chunk.metadata?.rule_strength,
            relevance: chunk.relevance_score,
            full_text: chunk.text
        });
    }
    
    /**
     * Jump to citation in document panel
     */
    jumpToCitation(citationId) {
        this.scrollToHighlight(citationId);
        
        // Highlight the element temporarily
        const element = document.querySelector(`[data-chunk-id="${citationId}"]`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            element.classList.add('highlight-pulse');
            setTimeout(() => {
                element.classList.remove('highlight-pulse');
            }, 2000);
        }
    }
    
    /**
     * Scroll to specific highlight in document panel
     */
    scrollToHighlight(chunkId) {
        const element = document.querySelector(`.document-viewer [data-chunk-id="${chunkId}"]`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    /**
     * Show evidence container
     */
    showEvidenceContainer() {
        const container = document.querySelector('.evidence-container');
        if (container) {
            container.style.display = 'grid';
            container.classList.add('fade-in');
        }
    }
    
    /**
     * Hide evidence container
     */
    hideEvidenceContainer() {
        const container = document.querySelector('.evidence-container');
        if (container) {
            container.style.display = 'none';
        }
    }
    
    /**
     * Truncate text to specified length
     */
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
    /**
     * Generate evidence report
     */
    generateEvidenceReport() {
        if (!this.currentDecision || !this.currentEvidence.length) {
            alert('No evidence data available for report generation');
            return;
        }
        
        const report = {
            decision: this.currentDecision,
            evidence: this.currentEvidence,
            timestamp: new Date().toISOString(),
            summary: this.generateEvidenceSummary()
        };
        
        // Download as JSON
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `evidence-report-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    /**
     * Generate evidence summary
     */
    generateEvidenceSummary() {
        if (!this.currentEvidence.length) return 'No evidence available';
        
        const ruleStrengths = this.currentEvidence.map(e => e.metadata?.rule_strength || 'informational');
        const avgRelevance = this.currentEvidence.reduce((sum, e) => sum + (e.relevance_score || 0), 0) / this.currentEvidence.length;
        
        return {
            total_chunks: this.currentEvidence.length,
            average_relevance: Math.round(avgRelevance * 100),
            rule_strength_distribution: ruleStrengths.reduce((acc, strength) => {
                acc[strength] = (acc[strength] || 0) + 1;
                return acc;
            }, {}),
            primary_sources: [...new Set(this.currentEvidence.map(e => e.doc_title))],
            confidence_level: this.currentDecision.confidence || 0
        };
    }
}

// Initialize Evidence UI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.evidenceUI = new EvidenceUI();
    console.log('🎯 Evidence UI initialized');
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EvidenceUI;
}
