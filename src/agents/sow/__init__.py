"""Source of Wealth (SOW) extraction agents.

This module contains all specialized agents for extracting different types
of wealth sources (employment, property, business, gifts, etc.).
"""

from src.agents.sow.employment_agent import EmploymentIncomeAgent
from src.agents.sow.property_agent import PropertySaleAgent
from src.agents.sow.business_income_agent import BusinessIncomeAgent
from src.agents.sow.business_dividends_agent import BusinessDividendsAgent
from src.agents.sow.gift_agent import GiftAgent
from src.agents.sow.inheritance_agent import InheritanceAgent
from src.agents.sow.divorce_agent import DivorceSettlementAgent
from src.agents.sow.business_sale_agent import SaleOfBusinessAgent
from src.agents.sow.asset_sale_agent import SaleOfAssetAgent
from src.agents.sow.lottery_agent import LotteryWinningsAgent
from src.agents.sow.insurance_agent import InsurancePayoutAgent

__all__ = [
    "EmploymentIncomeAgent",
    "PropertySaleAgent",
    "BusinessIncomeAgent",
    "BusinessDividendsAgent",
    "GiftAgent",
    "InheritanceAgent",
    "DivorceSettlementAgent",
    "SaleOfBusinessAgent",
    "SaleOfAssetAgent",
    "LotteryWinningsAgent",
    "InsurancePayoutAgent",
]
