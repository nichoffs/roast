import os
import shutil

import databases
import requests
from deepface import DeepFace
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database setup (SQLite)
DATABASE_URL = "sqlite:///./roast.db"
database = databases.Database(DATABASE_URL)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database models
class Roastee(Base):
    __tablename__ = "roastees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)


class Roast(Base):
    __tablename__ = "roasts"
    id = Column(Integer, primary_key=True, index=True)
    roastee_id = Column(Integer, ForeignKey("roastees.id"))
    roast_text = Column(String)


# Create tables
Base.metadata.create_all(bind=engine)

# Directory for roastee photos
DB_PATH = "db_path"
os.makedirs(DB_PATH, exist_ok=True)

# API configurations
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

DISTANCE_THRESHOLD = 0.4


# Serve HTML page
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


# List roastees for dropdown
@app.get("/roastees_list")
async def list_roastees():
    db = SessionLocal()
    roastees = db.query(Roastee).all()
    db.close()
    return [{"id": r.id, "name": r.name} for r in roastees]


# Get all roastees and roasts data
@app.get("/data")
async def get_data():
    db = SessionLocal()
    roastees = db.query(Roastee).all()
    data = []
    for roastee in roastees:
        roasts = db.query(Roast).filter(Roast.roastee_id == roastee.id).all()
        data.append(
            {
                "id": roastee.id,
                "name": roastee.name,
                "roasts": [roast.roast_text for roast in roasts],
            }
        )
    db.close()
    return data


# Add a roastee
@app.post("/roastees/")
async def add_roastee(name: str = Form(...), photos: list[UploadFile] = File(...)):
    db = SessionLocal()
    roastee = Roastee(name=name)
    db.add(roastee)
    db.commit()
    db.refresh(roastee)
    roastee_id = roastee.id

    roastee_folder = os.path.join(DB_PATH, str(roastee_id))
    os.makedirs(roastee_folder, exist_ok=True)

    for photo in photos:
        file_path = os.path.join(roastee_folder, photo.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

    db.close()
    return {"message": f"Roastee '{name}' added"}


# Add a roast
@app.post("/roasts/")
async def add_roast(roastee_id: int = Form(...), roast_text: str = Form(...)):
    db = SessionLocal()
    roast = Roast(roastee_id=roastee_id, roast_text=roast_text)
    db.add(roast)
    db.commit()
    db.close()
    return {"message": f"Roast added to roastee ID {roastee_id}"}


# Process frame from Raspberry Pi
@app.post("/process_frame/")
async def process_frame(frame: UploadFile = File(...)):
    temp_path = "temp_frame.jpg"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(frame.file, buffer)

    try:
        dfs = DeepFace.find(
            img_path=temp_path,
            db_path=DB_PATH,
            model_name="VGG-Face",
            distance_metric="cosine",
            detector_backend="opencv",
        )

        if len(dfs) == 0:
            return {"message": "No faces detected"}

        for df in dfs:
            if not df.empty:
                top_match = df.iloc[0]
                if top_match["distance"] < DISTANCE_THRESHOLD:
                    match_path = top_match["identity"]
                    roastee_id = int(os.path.basename(os.path.dirname(match_path)))

                    db = SessionLocal()
                    roastee = db.query(Roastee).filter(Roastee.id == roastee_id).first()
                    roasts = (
                        db.query(Roast).filter(Roast.roastee_id == roastee_id).all()
                    )
                    roast_texts = [roast.roast_text for roast in roasts]
                    db.close()

                    prompt = f"Roastee: {roastee.name}\nExisting Roasts: {', '.join(roast_texts)}"
                    payload = {
                        "model": "r1-1776",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a roast master. Write a funny roast.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                    }
                    headers = {
                        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json",
                    }
                    response = requests.post(
                        PERPLEXITY_API_URL, json=payload, headers=headers
                    )
                    response.raise_for_status()
                    generated_roast = response.json()["choices"][0]["message"][
                        "content"
                    ]

                    audio = client.text_to_speech.convert(
                        text=generated_roast,
                        voice_id="JBFqnCBsd6RMkjVDRZzb",
                        model_id="eleven_multilingual_v2",
                        output_format="mp3_44100_128",
                    )

                    return StreamingResponse(audio, media_type="audio/mpeg")

        return {"message": "No matching roastee found"}
    except Exception as e:
        return {"message": f"Error: {str(e)}"}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
