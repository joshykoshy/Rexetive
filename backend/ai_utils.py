import os
from openai import OpenAI
import json
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()


openai = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))

async def evaluate_submission(case_text: str, user_text: str, category: str):
    try:
        if category == "synopsis":
            prompt = f"""
                    You are an AI assistant reviewing a user-submitted theory on a public case. Analyze the following case and the user submitted theory:
                    Case: {case_text}
                    User Submitted Theory: {user_text} 

                    and provide:
                    1. Clarity (0-10): How clearly is the theory communicated?
                    2. Plausibility (0-10): Is the theory realistic based on known facts or reasoning?
                    3. Consistency (0-10): Does the theory contradict itself or known timelines?
                    4. Relevance (0-10): Is the theory on-topic and tied to the case?
                    5. Flag (text): Flag contradictions or timeline errors (e.g. person in two places, unsupported motive) if any.
                    6. is_safe (bool): If any part of the theory contains harmful, explicit, or offensive material, set `is_safe` to false.
                    7. Summary (text): Provide a short summary and constructive feedback.
                    8. Rank [Gold, Silver, Bronze, None]: Rank the theory based on the above criteria.
                    
                    Return your analysis in valid JSON format with the following keys: clarity, plausibility, consistency, relevance, flag, is_safe, summary, rank.
            """
        elif category == "logic":
            prompt = f"""
                    You are an AI assistant verifying the timeline and logic of a submitted theory. Check the following:
                    Case: {case_text}
                    User Submitted Theory: {user_text}

                    Provide:
                    1. Inconsistencies (list): List detected contradictions or impossible events.
                    2. Missing Links (list): Identify major gaps or unsupported jumps in the story.
                    3. Timeline Validity (0-10): Score how well the chronology matches known facts.
                    4. Conflict Summary (text): Explain major timeline issues simply.
                    5. Correction Suggestions (text): Recommend ways the user could fix timeline problems.

                    Return your analysis in valid JSON with: inconsistencies, missing_links, timeline_validity, conflict_summary, correction_suggestions.
            """
        elif category == "hypothesis":
            prompt = f"""
                    You are an AI assistant critically evaluating a hypothesis about a case.
                    Case Details: {case_text}
                    User Hypothesis: {user_text}

                    Provide:
                    1. Plausibility Assessment (0-10): How likely is the hypothesis based on known facts?
                    2. Counterpoints (list): Logical counter-arguments or alternative explanations.
                    3. Evidence Match (text): Indicate whether supporting evidence exists for the hypothesis.
                    4. Suggest Further Investigation (text): Recommend what additional evidence could confirm or refute the hypothesis.

                    Return the output as valid JSON with: plausibility_assessment, counterpoints, evidence_match, suggest_further_investigation.
            """
        elif category == "bias":
            prompt = f"""
                    You are an AI assistant identifying bias in case theories.
                    Case Details: {case_text}
                    User Submission: {user_text}

                    Provide:
                    1. Detected Biases (list): List any confirmation bias, emotional bias, or logical fallacies.
                    2. Objectivity Score (0-10): Rate how objective the theory is.
                    3. Challenge Points (list): Questions or prompts that encourage rethinking the theory.
                    4. Bias Impact Summary (text): Explain how the biases might mislead the investigation.

                    Return in valid JSON: detected_biases, objectivity_score, challenge_points, bias_impact_summary.
            """
        response = openai.chat.completions.create(
            model = "gpt-4",
            messages = [{"role": "user", "content": prompt}] 
        )

        data = json.loads(response.choices[0].message.content)
        if category == "synopsis":
            if (data.get('clarity', 0) + data.get('plausibility', 0) + data.get('consistency',0) + data.get('relevance',0)) >= 30 and data.get('is_safe', True):
                data['is_valid'] = True
            else:
                data['is_valid'] = False
        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating submission: {str(e)}")
