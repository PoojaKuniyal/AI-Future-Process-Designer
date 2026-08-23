import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from backend.app.config import settings
from backend.app.database import get_db, init_db
from backend.app import models, schemas, seed
from backend.app.agents.graph import run_transformation_workflow

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Future Process Designer API",
    description="Backend API powering multi-agent business process analysis and future-state design.",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    logger.info("Starting up FastAPI application...")
    init_db()
    
    # Auto-seed Shopify retail operations data on startup
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        seeded_count = seed.seed_retail_data(db)
        if seeded_count > 0:
            logger.info(f"Database auto-seeded with {seeded_count} Shopify retail activities.")
    except Exception as e:
        logger.error(f"Auto-seeding failed: {e}")
    finally:
        db.close()


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "model": settings.LLM_MODEL, "provider": settings.LLM_PROVIDER}


@app.get("/api/processes", response_model=List[schemas.ProcessResponse])
def get_processes(db: Session = Depends(get_db)):
    processes = db.query(models.Process).order_by(models.Process.created_at.desc()).all()
    return processes


@app.get("/api/processes/{process_id}", response_model=schemas.ProcessDetailResponse)
def get_process_detail(process_id: str, db: Session = Depends(get_db)):
    process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    # Query related objects with joint joins or manual mapping
    current_activities = db.query(models.CurrentActivity).filter(models.CurrentActivity.process_id == process_id).all()
    future_activities = db.query(models.FutureActivity).filter(models.FutureActivity.process_id == process_id).all()
    opportunities = db.query(models.AIOpportunity).filter(models.AIOpportunity.process_id == process_id).all()
    
    # Pre-load evidence analyses along with source citations
    analyses = db.query(models.EvidenceAnalysis).join(models.CurrentActivity).filter(models.CurrentActivity.process_id == process_id).all()
    
    # Load relationships
    relationships = db.query(models.EvidenceRelationship).join(models.FutureActivity).filter(models.FutureActivity.process_id == process_id).all()

    # Build schema payload manually to ensure nested sources are attached
    serialized_analyses = []
    for analysis in analyses:
        source_citation = db.query(models.ResearchSource).filter(models.ResearchSource.id == analysis.source_id).first()
        serialized_analyses.append(
            schemas.EvidenceAnalysisResponse(
                id=analysis.id,
                source_id=analysis.source_id,
                activity_id=analysis.activity_id,
                problem=analysis.problem,
                technology=analysis.technology,
                how_it_works=analysis.how_it_works,
                applicability_why=analysis.applicability_why,
                parts_to_automate=analysis.parts_to_automate,
                human_control=analysis.human_control,
                systems_roles_affected=analysis.systems_roles_affected,
                future_state_description=analysis.future_state_description,
                evidence_summary=analysis.evidence_summary,
                source=schemas.ResearchSourceResponse.model_validate(source_citation) if source_citation else None
            )
        )

    return schemas.ProcessDetailResponse(
        id=process.id,
        industry=process.industry,
        name=process.name,
        created_at=process.created_at,
        current_activities=[schemas.CurrentActivityResponse.model_validate(c) for c in current_activities],
        future_activities=[schemas.FutureActivityResponse.model_validate(f) for f in future_activities],
        opportunities=[schemas.AIOpportunityResponse.model_validate(o) for o in opportunities],
        analyses=serialized_analyses,
        relationships=[schemas.EvidenceRelationshipResponse.model_validate(r) for r in relationships]
    )


@app.post("/api/processes/run", response_model=schemas.ProcessResponse)
async def run_process_transformation(req: schemas.ProcessRunRequest, db: Session = Depends(get_db)):
    logger.info(f"Received request to analyze: {req.industry} -> {req.process_name}")
    
    # 1. Create a new process record
    process = models.Process(
        industry=req.industry,
        name=req.process_name
    )
    db.add(process)
    db.commit()
    db.refresh(process)

    # 2. Run LangGraph workflow synchronously for simplicity/instant display
    # (FastAPI handles it as async endpoint)
    final_state = await run_transformation_workflow(
        process_id=process.id,
        industry=req.industry,
        process_name=req.process_name,
        search_provider=settings.SEARCH_PROVIDER
    )
    
    if final_state.get("error"):
        logger.error(f"LangGraph run ended with errors: {final_state['error']}")
        raise HTTPException(status_code=500, detail=final_state["error"])
        
    return process


@app.post("/api/processes/{process_id}/transform", response_model=schemas.ProcessResponse)
async def transform_existing_process(process_id: str, db: Session = Depends(get_db)):
    process = db.query(models.Process).filter(models.Process.id == process_id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
        
    final_state = await run_transformation_workflow(
        process_id=process.id,
        industry=process.industry,
        process_name=process.name,
        search_provider=settings.SEARCH_PROVIDER
    )
    
    if final_state.get("error"):
        logger.error(f"LangGraph transformation run failed: {final_state['error']}")
        raise HTTPException(status_code=500, detail=final_state["error"])
        
    return process


@app.post("/api/seed")
def seed_database(db: Session = Depends(get_db)):
    seeded_count = seed.seed_retail_data(db)
    return {"message": f"Database seeding complete. Seeded {seeded_count} activities."}


@app.get("/api/config/search")
def get_search_config():
    return {"search_provider": settings.SEARCH_PROVIDER}


@app.post("/api/config/search")
def update_search_config(cfg: schemas.SearchConfigUpdate):
    provider = cfg.search_provider.strip().lower()
    if provider not in ["tavily", "brave"]:
        raise HTTPException(status_code=400, detail="Search provider must be 'tavily' or 'brave'")
    settings.SEARCH_PROVIDER = provider
    logger.info(f"Search provider updated dynamically to: {provider}")
    return {"message": "Config updated successfully", "search_provider": settings.SEARCH_PROVIDER}
