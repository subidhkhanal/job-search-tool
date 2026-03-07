from fastapi import APIRouter, Depends
from groq import Groq

from ..dependencies import get_groq_client
from ..models.schemas import (
    ColdDMRequest,
    CoverLetterRequest,
    DemoOutreachRequest,
    FollowUpRequest,
    ReferralRequestBody,
    ThankYouRequest,
)
from message_generator import (
    generate_cold_dm,
    generate_cover_letter,
    generate_demo_outreach,
    generate_follow_up,
    generate_referral_request,
    generate_thank_you,
)

router = APIRouter()


@router.post("/cold-dm")
def cold_dm(
    body: ColdDMRequest,
    client: Groq = Depends(get_groq_client),
):
    content = generate_cold_dm(
        client,
        company_name=body.company,
        role_title=body.role,
        company_description=body.company_desc,
        platform=body.platform,
        project_link=body.project_link,
    )
    return {"content": content}


@router.post("/follow-up")
def follow_up(
    body: FollowUpRequest,
    client: Groq = Depends(get_groq_client),
):
    content = generate_follow_up(
        client,
        company_name=body.company,
        role_title=body.role,
        days_since_applied=body.days,
        original_platform=body.platform,
        follow_up_number=body.follow_up_number,
    )
    return {"content": content}


@router.post("/cover-letter")
def cover_letter(
    body: CoverLetterRequest,
    client: Groq = Depends(get_groq_client),
):
    content = generate_cover_letter(
        client,
        company_name=body.company,
        role_title=body.role,
        job_description=body.jd,
        company_info=body.company_info,
    )
    return {"content": content}


@router.post("/thank-you")
def thank_you(
    body: ThankYouRequest,
    client: Groq = Depends(get_groq_client),
):
    content = generate_thank_you(
        client,
        company_name=body.company,
        interviewer_name=body.interviewer,
        key_discussion_point=body.discussion,
    )
    return {"content": content}


@router.post("/referral-request")
def referral_request(
    body: ReferralRequestBody,
    client: Groq = Depends(get_groq_client),
):
    content = generate_referral_request(
        client,
        contact_name=body.contact_name,
        contact_role=body.contact_role,
        company=body.company,
        role_applying_for=body.role_applying_for,
        relationship=body.relationship,
    )
    return {"content": content}


@router.post("/demo-outreach")
def demo_outreach(
    body: DemoOutreachRequest,
    client: Groq = Depends(get_groq_client),
):
    content = generate_demo_outreach(
        client,
        company=body.company,
        role=body.role,
        demo_url=body.demo_url,
        demo_description=body.demo_description,
        company_desc=body.company_desc,
    )
    return {"content": content}
