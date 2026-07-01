# app/services/lead_capture.py

import logging
from typing import Union

from app.core.models import LeadData
from app.db.operations import insert_captured_lead


logger = logging.getLogger("mtca")


async def process_and_save_qualified_lead(
    org_id: str,
    branch_id: str, 
    lead_data: Union[LeadData, dict],
    user_email: str,
    username: str
) -> str:
    """
    Domain service responsible for processing and saving qualified leads.

    Flow:
    LangGraph Lead Node
        |
        v
    Lead Service
        |
        v
    Mongo CRUD layer
    """

    logger.info(
        f"""
PROCESSING QUALIFIED LEAD
-------------------------
Organization : {org_id}
Branch       : {branch_id}
Username     : {username}
Email        : {user_email}
"""
    )


    # ---------------------------------------------------------
    # Normalize Lead Data
    # ---------------------------------------------------------

    if isinstance(lead_data, LeadData):
        lead_dict = lead_data.model_dump()

    elif isinstance(lead_data, dict):
        lead_dict = lead_data

    else:
        raise TypeError(
            "lead_data must be LeadData or dict"
        )


    # ---------------------------------------------------------
    # Identity Validation
    # ---------------------------------------------------------

    if not user_email:
        raise ValueError(
            "Cannot save lead without authenticated user email"
        )

    if not username:
        raise ValueError(
            "Cannot save lead without authenticated username"
        )


    # ---------------------------------------------------------
    # Database Insert
    # ---------------------------------------------------------

    inserted_id = await insert_captured_lead(
        org_id=org_id,
        branch_id=branch_id,
        lead_dict=lead_dict,
        user_email=user_email,
        username=username,
    )


    logger.info(
        f"""
LEAD SAVED SUCCESSFULLY
-----------------------
Mongo ID: {inserted_id}
"""
    )


    return inserted_id