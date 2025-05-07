import sqlite3
from fastapi import FastAPI, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import json
from ai_utils import evaluate_submission
from blockchain_utils import submit_to_chain, mint_nft, get_submission_from_chain, all_submissions
from user_auth import add_auth_routes, get_current_user, User, update_user_reputation


# Test the backend with other addresses
app = FastAPI()

add_auth_routes(app)

class SubmissionRequest(BaseModel):
    caseId: int
    case: str
    theory: str

class SubmissionResponse(BaseModel):
    caseId: int
    author: str
    clarity: int
    plausibility: int
    consistency: int
    relevance: int
    is_safe: bool
    flag: str
    theory: str
    summary: str
    rank: str
    is_valid: bool
    submission_id: Optional[int] = None
    blockchain_tx: Optional[Dict[str, Any]] = None
    nft_minted: bool = False
    timestamp: int = None
    reputation_updated: bool = False

class ViewSubmission(BaseModel):
    caseId: int
    author: str
    clarity: int
    plausibility: int
    consistency: int
    relevance: int
    is_safe: bool
    flag: str
    theory: str
    summary: str
    rank: str
    is_valid: bool
    submission_id: Optional[int] = None
    timestamp: int = None

@app.post("/submit_submission/synopsis", response_model=SubmissionResponse)
async def submit_submission(
    request: SubmissionRequest, 
    current_user: User = Depends(get_current_user)
):
    author = current_user.wallet_address
    
    evaluation = await evaluate_submission(case_text=request.case, user_text=request.theory, category="synopsis")

    timestamp = int(datetime.now().timestamp())
    blockchain_tx = None
    nft_minted = False
    reputation_updated = False
    submission_id = None

    if evaluation['is_valid']:
        try:
            print("Submitting to blockchain...")
            blockchain_result = await run_in_threadpool(
                submit_to_chain,
                request.caseId,
                author,
                evaluation['clarity'],
                evaluation['plausibility'],
                evaluation['consistency'],
                evaluation['relevance'],
                evaluation['is_safe'],
                evaluation['flag'],
                request.theory,
                evaluation['summary'],
                evaluation['rank'],
                timestamp
            )

            print("Submitted to blockchain")
            print("Blockchain submission result:", blockchain_result)

            blockchain_tx = json.dumps(blockchain_result)
            nft_minted = blockchain_result.get('nft_minted', False)
            submission_id = blockchain_result.get('submission_id', None)

            total_score = evaluation['clarity'] + evaluation['plausibility'] + evaluation['consistency'] + evaluation['relevance']
            reputation_points = 0
            
            if total_score >= 30:
                reputation_points = 10  
            elif total_score >= 25:
                reputation_points = 5   
            elif total_score >= 20:
                reputation_points = 2   
            else:
                reputation_points = 1 
                
            if nft_minted:
                reputation_points += 5
                
            if reputation_points > 0:
                reputation_updated = await update_user_reputation(
                    author, 
                    reputation_points, 
                    nft_minted
                )
                
        except Exception as e:
            print("Blockchain submission failed:", e)

    response = SubmissionResponse(
        caseId=request.caseId,
        author=author,
        clarity=evaluation['clarity'],
        plausibility=evaluation['plausibility'],
        consistency=evaluation['consistency'],
        relevance=evaluation['relevance'],
        is_safe=evaluation['is_safe'],
        flag=evaluation['flag'],
        theory=request.theory,
        summary=evaluation['summary'],
        rank=evaluation['rank'],
        is_valid=evaluation['is_valid'],
        submission_id=submission_id,
        blockchain_tx=json.loads(blockchain_tx) if blockchain_tx else None,
        nft_minted=nft_minted,
        timestamp=timestamp,
        reputation_updated=reputation_updated
    )

    status_code = 200 if evaluation['is_valid'] else 220

    return JSONResponse(
        content=response.dict(),
        status_code=status_code
    )

@app.post("/submit_submission/logic")
async def submit_logic_submission(
    request: SubmissionRequest, 
    current_user: User = Depends(get_current_user)
):
    author = current_user.wallet_address
    evaluation = await evaluate_submission(case_text=request.case, user_text=request.theory, category="logic")
    
    response = {
        "author": author,
        "inconsistencies": evaluation.get('inconsistencies', []),
        "missing_links": evaluation.get('missing_links', []),
        "timeline_validity": evaluation.get('timeline_validity', 0),
        "conflict_summary": evaluation.get('conflict_summary', ""),
        "correction_suggestions": evaluation.get('correction_suggestions', "")
    }
    return JSONResponse(
        content=response,
        status_code=200
    )

@app.post("/submit_submission/hypothesis")
async def submit_hypothesis_submission(
    request: SubmissionRequest, 
    current_user: User = Depends(get_current_user)
):
    author = current_user.wallet_address
    evaluation = await evaluate_submission(case_text=request.case, user_text=request.theory, category="hypothesis")
    
    response = {
        "author": author,
        "plausibility_assessment": evaluation.get('plausibility_assessment', 0),
        "counterpoints": evaluation.get('counterpoints', []),
        "evidence_match": evaluation.get('evidence_match', ""),
        "suggest_further_investigation": evaluation.get('suggest_further_investigation', "")
    }
    return JSONResponse(
        content=response,
        status_code=200
    )
@app.post("/submit_submission/bias")
async def submit_bias_submission(
    request: SubmissionRequest, 
    current_user: User = Depends(get_current_user)
):
    author = current_user.wallet_address
    evaluation = await evaluate_submission(case_text=request.case, user_text=request.theory, category="bias")
    
    response = {
        "author": author,
        "detected_biases": evaluation.get('detected_biases', []),
        "objectivity_score": evaluation.get('objectivity_score', 0),
        "challenge_points": evaluation.get('challenge_points', []),
        "bias_impact_summary": evaluation.get('bias_impact_summary', "")
    }
    return JSONResponse(
        content=response,
        status_code=200
    )

@app.get("/get_submission/{submission_id}")
async def get_submission(submission_id: int, current_user: User = Depends(get_current_user)):
    submission_data = await get_submission_from_chain(submission_id)
    print("Submission data:", submission_data)
    if not submission_data:
        raise HTTPException(status_code=404, detail="Submission not found")

    total_score = int(submission_data['clarity']) + int(submission_data['plausibility']) + int(submission_data['consistency']) + int(submission_data['relevance'])

    response = ViewSubmission(
        caseId=int(submission_data['caseId']),
        author=str(submission_data['author']),
        clarity=int(submission_data['clarity']),
        plausibility=int(submission_data['plausibility']),
        consistency=int(submission_data['consistency']),
        relevance=int(submission_data['relevance']),
        is_safe=bool(submission_data['is_safe']),
        flag=str(submission_data['flag']),
        theory=str(submission_data['theory']),
        summary=str(submission_data['summary']),
        rank=str(submission_data['rank']),
        is_valid= total_score >= 30 and bool(submission_data['is_safe']),
        timestamp=int(submission_data['timestamp']),
        submission_id=submission_id,
    )
    return JSONResponse(
        content=response.dict(),
    )

@app.get("/get_all_submissions")
async def get_all_submissions(current_user: User = Depends(get_current_user)):
    submissions = await all_submissions()
    if not submissions:
        raise HTTPException(status_code=404, detail="No submissions found")
    
    results = []
    for submission_data in submissions:
        total_score = int(submission_data['clarity']) + int(submission_data['plausibility']) + int(submission_data['consistency']) + int(submission_data['relevance'])

        response = ViewSubmission(
            caseId=int(submission_data['caseId']),
            author=str(submission_data['author']),
            clarity=int(submission_data['clarity']),
            plausibility=int(submission_data['plausibility']),
            consistency=int(submission_data['consistency']),
            relevance=int(submission_data['relevance']),
            is_safe=bool(submission_data['is_safe']),
            flag=str(submission_data['flag']),
            theory=str(submission_data['theory']),
            summary=str(submission_data['summary']),
            rank=str(submission_data['rank']),
            is_valid= total_score >= 30 and bool(submission_data['is_safe']),
            timestamp=int(submission_data['timestamp']),
            submission_id=submission_data['submission_id'],
        )
        results.append(response.dict())

    return results

@app.get("/get_all_submissions/case/{caseId}")
async def get_all_submissions_by_case(caseId: int, current_user: User = Depends(get_current_user)):
    submissions = await all_submissions()
    if not submissions:
        raise HTTPException(status_code=404, detail="No submissions found for this case")
    
    results = []
    for submission_data in submissions:
        if int(submission_data['caseId']) != caseId:
            continue
        total_score = int(submission_data['clarity']) + int(submission_data['plausibility']) + int(submission_data['consistency']) + int(submission_data['relevance'])
        response = ViewSubmission(
            caseId=int(submission_data['caseId']),
            author=str(submission_data['author']),
            clarity=int(submission_data['clarity']),
            plausibility=int(submission_data['plausibility']),
            consistency=int(submission_data['consistency']),
            relevance=int(submission_data['relevance']),
            is_safe=bool(submission_data['is_safe']),
            flag=str(submission_data['flag']),
            theory=str(submission_data['theory']),
            summary=str(submission_data['summary']),
            rank=str(submission_data['rank']),
            is_valid= total_score >= 30 and bool(submission_data['is_safe']),
            timestamp=int(submission_data['timestamp']),
            submission_id=submission_data['submission_id'],
        )
        results.append(response.dict())

    return results

@app.get("/get_all_submissions/author/{author}")
async def get_all_submissions_by_author(current_user: User = Depends(get_current_user)):
    submissions = await all_submissions()
    author = current_user.wallet_address
    if not submissions:
        raise HTTPException(status_code=404, detail="No submissions found for this author")
    
    results = []
    for submission_data in submissions:
        if submission_data['author'] != author:
            continue
        total_score = int(submission_data['clarity']) + int(submission_data['plausibility']) + int(submission_data['consistency']) + int(submission_data['relevance'])

        response = ViewSubmission(
            caseId=int(submission_data['caseId']),
            author=str(submission_data['author']),
            clarity=int(submission_data['clarity']),
            plausibility=int(submission_data['plausibility']),
            consistency=int(submission_data['consistency']),
            relevance=int(submission_data['relevance']),
            is_safe=bool(submission_data['is_safe']),
            flag=str(submission_data['flag']),
            theory=str(submission_data['theory']),
            summary=str(submission_data['summary']),
            rank=str(submission_data['rank']),
            is_valid= total_score >= 30 and bool(submission_data['is_safe']),
            timestamp=int(submission_data['timestamp']),
            submission_id=submission_data['submission_id'],
        )
        results.append(response.dict())

    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)