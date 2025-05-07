from pysui import SyncClient, SuiConfig, handle_result
from pysui.sui.sui_txn import SyncTransaction
from pysui.sui.sui_types import ObjectID
from pysui.sui.sui_types import SuiAddress, SuiU64, SuiU8
from fastapi import HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

SUI_RPC_URL = os.getenv("SUI_RPC_URL")
SUI_PRIVATE_KEY = os.getenv("SUI_PRIVATE_KEY")
SUI_ADDRESS = os.getenv("SUI_ADDRESS")
PACKAGE_ID = os.getenv("PREDICTIONS_PACKAGE_ID")
SUBMISSIONS_OBJECT_ID = os.getenv("SUBMISSIONS_OBJECT_ID")
MODULE_NAME = os.getenv("PREDICTIONS_MODULE_NAME")
GAS_BUDGET = os.getenv("GAS_BUDGET")

sui_config = SuiConfig.user_config(
    rpc_url=SUI_RPC_URL,
    prv_keys=[SUI_PRIVATE_KEY]
)
sui_client = SyncClient(sui_config)



def submit_to_chain(
        caseId: int,
        author: str,
        clarity: int,
        plausibility: int,
        consistency: int,
        relevance: int,
        is_safe: bool,
        flag: str,
        theory: str,
        summary: str,
        rank: str,
        timestamp: int
):
    try:
        tx = SyncTransaction(client=sui_client)
        submissions_obj = ObjectID(SUBMISSIONS_OBJECT_ID)

        tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::submit_submission",
            arguments=[
                submissions_obj,
                SuiU64(caseId),
                SuiAddress(author),
                SuiU8(clarity),
                SuiU8(plausibility),
                SuiU8(consistency),
                SuiU8(relevance),
                is_safe,
                flag,
                theory,
                summary,
                rank,
                SuiU64(timestamp)
            ]
        )

        result = handle_result(tx.execute())

        submission_id = None

        if result and hasattr(result, 'effects') and result.effects.status.status == "success":
            if hasattr(result, 'events'):
                for event in result.events:
                    if event.event_type == f"{PACKAGE_ID}::{MODULE_NAME}::SubmissionSubmitted":
                        submission_id = int(event.parsed_json['id'])
                        break

            if submission_id is None:
                raise HTTPException(
                    status_code=500,
                    detail="Submission ID not found in events"
                )

            # Handle NFT minting
            nft_minted = False
            score = clarity + plausibility + consistency + relevance

            if clarity >= 6 and plausibility >= 6 and consistency >= 6 and relevance >= 6 and score >= 30 and is_safe:
                nft_result = mint_nft(caseId, author, score, summary, rank, timestamp)
                if nft_result and nft_result.get("status") == "success":
                    nft_minted = True
                else:
                    print(f"NFT minting encountered an error")

            return {
                "submission_id": submission_id,
                "tx_digest": result.digest,
                "status": "success",
                "nft_minted": nft_minted
            }

        raise HTTPException(
            status_code=500,
            detail=f"Transaction failed with status: {result.effects.status if result and hasattr(result, 'effects') else 'unknown'}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting to chain: {str(e)}"
        )

def mint_nft(
        caseId: int,
        author: str,
        score: int,
        summary: str,
        rank: str,
        timestamp: int
):
    try:
        tx = SyncTransaction(client=sui_client)

        tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::mint_nft",
            arguments=[
                SuiU64(caseId),
                SuiAddress(author),
                SuiU8(score),
                summary,
                rank,
                SuiU64(timestamp)
            ]
        )

        result = handle_result(tx.execute())

        print("NFT minting result:") 
        print(result.to_json(indent=2)) 

        if result and hasattr(result, 'effects') and result.effects.status.status == "success":
            return {
                "tx_digest": result.digest,
                "status": "success"
            }
        raise HTTPException(
            status_code=500,
            detail=f"NFT minting failed with status: {result.effects.status if result and hasattr(result, 'effects') else 'unknown'}"
        )            

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"NFT minting failed: {str(e)}"
        )

async def get_submission_from_chain(submission_id: int):
    try:
        submissions_obj = ObjectID(SUBMISSIONS_OBJECT_ID)

        count_tx = SyncTransaction(client=sui_client)
        count_tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::get_submissions_count",
            arguments=[submissions_obj]
        )

        count_result = handle_result(count_tx.execute())
        print("Count result:", count_result.to_json(indent=2))
        
        if count_result or hasattr(count_result, 'effects') or count_result.effects.status.status == "success":
            if hasattr(count_result, 'events'):
                for event in count_result.events:
                    if event.event_type == f"{PACKAGE_ID}::{MODULE_NAME}::SubmissionCounter":
                        count = int(event.parsed_json['counter']) - 1
                        break
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving submission count: {count_result.effects.status if count_result and hasattr(count_result, 'effects') else 'unknown'}"
            )
        
        if submission_id > count:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        submission_tx = SyncTransaction(client=sui_client)
        submission_tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::get_submission",
            arguments=[submissions_obj, SuiU64(submission_id)]
        )

        submission_result = handle_result(submission_tx.execute())
        print("Submission result:", submission_result.to_json(indent=2))
        
        if submission_result or hasattr(submission_result, 'effects') or submission_result.effects.status.status == "success":
            if hasattr(submission_result, 'events'):
                for event in submission_result.events:
                    if event.event_type == f"{PACKAGE_ID}::{MODULE_NAME}::ViewSubmission":
                        submission_data = event.parsed_json
                        return submission_data
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving submission: {submission_result.effects.status if submission_result and hasattr(submission_result, 'effects') else 'unknown'}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving submission from blockchain: {str(e)}"
        )
    
async def all_submissions():
    try:
        submissions_obj = ObjectID(SUBMISSIONS_OBJECT_ID)

        count_tx = SyncTransaction(client=sui_client)
        count_tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::get_submissions_count",
            arguments=[submissions_obj]
        )

        count_result = handle_result(count_tx.execute())
        print("Count result:", count_result.to_json(indent=2))
        
        if count_result or hasattr(count_result, 'effects') or count_result.effects.status.status == "success":
            if hasattr(count_result, 'events'):
                for event in count_result.events:
                    if event.event_type == f"{PACKAGE_ID}::{MODULE_NAME}::SubmissionCounter":
                        count = int(event.parsed_json['counter'])
                        break
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving submission count: {count_result.effects.status if count_result and hasattr(count_result, 'effects') else 'unknown'}"
            )

        submissions_count = count
        submissions = []
        for i in range(submissions_count):
            submission_tx = SyncTransaction(client=sui_client)
            submission_tx.move_call(
                target=f"{PACKAGE_ID}::{MODULE_NAME}::get_submission",
                arguments=[submissions_obj, SuiU64(i)]
            )
            submission_result = handle_result(submission_tx.execute())

            if submission_result or hasattr(submission_result, 'effects') or submission_result.effects.status.status == "success":
                if hasattr(submission_result, 'events'):
                    for event in submission_result.events:
                        if event.event_type == f"{PACKAGE_ID}::{MODULE_NAME}::ViewSubmission":
                            submission_data = event.parsed_json
                            submission_data['submission_id'] = i
                            submissions.append(submission_data)
        return submissions
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving submissions from blockchain: {str(e)}"
        )

