from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, course, dsa_coach


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    from app.core.checkpointer import close_checkpointer, init_checkpointer
    from app.agents.dsa_learn_agent import init_graph as init_learn_graph
    from app.agents.dsa_solve_agent import init_graph as init_solve_graph

    checkpointer = await init_checkpointer()
    if checkpointer is not None:
        init_learn_graph(checkpointer)
        init_solve_graph(checkpointer)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    await close_checkpointer()


app = FastAPI(title="AITutor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(course.router, prefix="/api/courses", tags=["courses"])
app.include_router(dsa_coach.router, prefix="/api/dsa-coach", tags=["dsa-coach"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

@app.get("/")
def root():
    return {"message": "Welcome to AITutor API"}
