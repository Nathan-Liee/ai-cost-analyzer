from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import csv
import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = FastAPI()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Cost Analyzer API"}

@app.post("/api/upload")
async def upload_logs(file: UploadFile = File(...), user_id: str = "test_user"):
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            lines = content.decode().split('\n')
            reader = csv.DictReader(lines)
            logs = list(reader)
        else:
            logs = json.loads(content)
        
        analysis = analyze_logs(logs)
        
        for log in logs:
            supabase.table("logs").insert({
                "user_id": user_id,
                "provider": log.get("provider", "openai"),
                "model": log.get("model"),
                "tokens": int(log.get("tokens", 0)) if log.get("tokens") else 0,
                "cost": float(log.get("cost", 0)) if log.get("cost") else 0
            }).execute()
        
        return {"success": True, "analysis": analysis}
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/analysis")
async def get_analysis(user_id: str = "test_user"):
    try:
        response = supabase.table("logs").select("*").eq("user_id", user_id).execute()
        logs = response.data
        analysis = analyze_logs(logs)
        return analysis
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/recommendations")
async def get_recommendations(user_id: str = "test_user"):
    try:
        response = supabase.table("logs").select("*").eq("user_id", user_id).execute()
        logs = response.data
        analysis = analyze_logs(logs)
        recommendations = generate_recommendations(analysis)
        
        return {
            "analysis": analysis,
            "recommendations": recommendations
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/recommendations")
async def post_recommendations(file: UploadFile = File(...), user_id: str = "test_user"):
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            lines = content.decode().split('\n')
            reader = csv.DictReader(lines)
            logs = list(reader)
        else:
            logs = json.loads(content)
        
        analysis = analyze_logs(logs)
        recommendations = generate_recommendations(analysis)
        
        for log in logs:
            try:
                supabase.table("logs").insert({
                    "user_id": user_id,
                    "provider": log.get("provider", "openai"),
                    "model": log.get("model"),
                    "tokens": int(log.get("tokens", 0)) if log.get("tokens") else 0,
                    "cost": float(log.get("cost", 0)) if log.get("cost") else 0
                }).execute()
            except:
                pass
        
        return {
            "analysis": analysis,
            "recommendations": recommendations
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_logs(logs):
    total_cost = 0
    by_model = {}
    
    for log in logs:
        try:
            tokens = int(log.get("tokens", 0)) if log.get("tokens") else 0
            model = log.get("model", "unknown")
            cost = calculate_cost(model, tokens)
            total_cost += cost
            
            if model not in by_model:
                by_model[model] = {"cost": 0, "tokens": 0}
            
            by_model[model]["cost"] += cost
            by_model[model]["tokens"] += tokens
        except:
            pass
    
    analysis = {
        "total_cost": round(total_cost, 2),
        "by_model": by_model,
        "count": len(logs)
    }
    analysis["recommendations"] = generate_recommendations(analysis)
    return analysis

def generate_recommendations(analysis):
    """Generate optimization recommendations"""
    recommendations = []
    by_model = analysis.get('by_model', {})
    total_cost = analysis.get('total_cost', 0)
    
    # 1. Model switching recommendation
    gpt4_cost = by_model.get('gpt-4', {}).get('cost', 0)
    if gpt4_cost > total_cost * 0.3:  # If GPT-4 > 30% of cost
        # Assume 40% of GPT-4 queries bisa pakai GPT-3.5
        potential_savings = (gpt4_cost * 0.4) * (1 - 0.0005/0.00003)  # rough calc
        recommendations.append({
            "type": "model_switch",
            "description": "Switch 40% of GPT-4 queries to GPT-3.5-turbo (10x cheaper)",
            "savings": round(potential_savings, 2),
            "savings_percent": round((potential_savings / total_cost) * 100, 1),
            "priority": "high"
        })
    
    # 2. Batch processing recommendation
    if total_cost > 10:  # Only if spend is significant
        batch_savings = total_cost * 0.15  # Assume 15% savings from batching
        recommendations.append({
            "type": "batching",
            "description": "Batch similar requests together (reduce overhead)",
            "savings": round(batch_savings, 2),
            "savings_percent": 15,
            "priority": "medium"
        })
    
    # 3. Claude recommendation (if heavy on GPT)
    gpt_total = (by_model.get('gpt-4', {}).get('cost', 0) + 
                 by_model.get('gpt-3.5-turbo', {}).get('cost', 0))
    if gpt_total > total_cost * 0.8:
        claude_savings = gpt_total * 0.3  # Claude 3 Sonnet is 10x cheaper
        recommendations.append({
            "type": "provider_switch",
            "description": "Consider Claude 3 Sonnet for similar tasks (3x cheaper than GPT-4)",
            "savings": round(claude_savings, 2),
            "savings_percent": round((claude_savings / total_cost) * 100, 1),
            "priority": "medium"
        })
    
    # Sort by savings
    recommendations.sort(key=lambda x: x['savings'], reverse=True)
    
    return recommendations

def calculate_cost(model, tokens):
    pricing = {
        "gpt-4": 0.00003,
        "gpt-3.5-turbo": 0.0005,
        "claude-3-opus": 0.000015,
        "claude-3-sonnet": 0.000003,
    }
    rate = pricing.get(model, 0.0001)
    return tokens * rate

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)