import os
import logging
from sqlalchemy.orm import Session
from backend.app import models
from datetime import datetime

logger = logging.getLogger(__name__)

def seed_retail_data(db: Session) -> int:
    """
    Seeds the PostgreSQL database with the initial Retail Store Operations dataset.
    """
    logger.info("Starting retail operations data seeding...")
    
    # Verify process doesn't exist to prevent double seeding
    existing_retail = db.query(models.Process).filter(models.Process.industry == "Retail").first()
    if existing_retail:
        logger.info("Retail operations data already seeded.")
        return 0

    # Define the structured dataset extracted from the retail operations data
    retail_processes = [
        {
            "name": "Inventory Management",
            "activities": [
                {
                    "name": "Inventory Stock Tracking & Counts",
                    "role": "Store Associate / Inventory Analyst",
                    "system": "ERP system & Paper spreadsheets",
                    "problem": "High shrinkage rate, phantom stock, and inaccurate physical cycle counts",
                    "evidence": "Inventory management involves tracking stock throughout the supply chain. Poor tracking leads to discrepancies, theft, and manual administrative errors."
                },
                {
                    "name": "Inventory Demand Forecasting",
                    "role": "Store Manager / Buyer",
                    "system": "Excel spreadsheet models",
                    "problem": "Costly stockouts of hot items and overstocking of slow-moving items causing capital lockup",
                    "evidence": "Sales forecasts are subject to changing conditions. Inaccurate forecasting leads to inventory distortion costing retailers trillions globally."
                },
                {
                    "name": "Stock Replenishment & Reordering",
                    "role": "Store Manager / Procurement Staff",
                    "system": "Manual Purchase Orders via Supplier portals",
                    "problem": "Long lead times, supply chain disruptions, and high shipping costs due to last-minute expedited shipping",
                    "evidence": "Reordering triggered manually or when threshold is hit. Expedited shipping is used to avoid stockouts when lead times are miscalculated."
                }
            ]
        },
        {
            "name": "Customer Service & Checkout",
            "activities": [
                {
                    "name": "Checkout Order & Payment Processing",
                    "role": "Cashier / Store Associate",
                    "system": "Point of Sale (POS) Hardware & Card Reader",
                    "problem": "Long checkout queue lines during peak hours and cashier error during manual entries",
                    "evidence": "Checkout queues and delays hinder retail productivity. An intuitive POS reduces transaction processing time."
                },
                {
                    "name": "Customer Loyalty & Reward Redemption",
                    "role": "Cashier",
                    "system": "Siloed loyalty program database / Shopify POS",
                    "problem": "Cashiers have to click through multiple screens/steps to look up points and apply rewards, causing queue delay",
                    "evidence": "Clothing retailer Mizzen+Main and Tomlinson's pet food reported checkout delays when cashiers had to click through extra steps to redeem loyalty rewards."
                },
                {
                    "name": "Fulfillment & Return Processing (BOPIS/BORIS)",
                    "role": "Store Associate",
                    "system": "Siloed eCommerce admin & POS systems",
                    "problem": "Processing online returns in-store (BORIS) or pickup (BOPIS) is a slow, manual logistical nightmare",
                    "evidence": "Integrating online and offline channels is challenging. Without unified systems, BOPIS/BORIS creates complex manual tracking for retail staff."
                }
            ]
        },
        {
            "name": "Employee Scheduling & Management",
            "activities": [
                {
                    "name": "Staff Scheduling & Time Tracking",
                    "role": "Store Manager",
                    "system": "Manual shift rosters & spreadsheet templates",
                    "problem": "Time-consuming administrative work for managers, scheduling conflicts, and labor cost inflation",
                    "evidence": "Managing employee rota schedules and shift swaps manually wastes hours of managerial time."
                },
                {
                    "name": "New Employee Onboarding & POS Training",
                    "role": "Store Manager / New Hire",
                    "system": "POS Training Mode / Manual checklists",
                    "problem": "High employee turnover means constant retraining; onboarding takes days and slows down checkout lines",
                    "evidence": "Retail industry faces high employee turnover. Bringing new staff up to speed on POS and policies requires substantial training time."
                }
            ]
        },
        {
            "name": "Store Safety, Security & Compliance",
            "activities": [
                {
                    "name": "Daily Opening & Closing Audits",
                    "role": "Store Manager / Closing Associate",
                    "system": "Paper checklist logs",
                    "problem": "Inconsistent compliance, administrative reconciliation errors, and lack of central visibility across locations",
                    "evidence": "Opening/closing checklists include till reconciliation, alarm tests, and floor walks. Paper logs are difficult to track centrally."
                },
                {
                    "name": "Loss Prevention & Shoplifting Control",
                    "role": "Store Associate / Security Staff",
                    "system": "CCTV camera monitors & staff observation",
                    "problem": "Shrinkage from shoplifting and staff internal fraud, and high cost of dedicated security guards",
                    "evidence": "Loss prevention measures include commercial insurance, staff training to detect counterfeit notes, and video monitoring."
                }
            ]
        },
        {
            "name": "Financial Management & Forecasting",
            "activities": [
                {
                    "name": "Sales Revenue Forecasting",
                    "role": "Store Manager",
                    "system": "Historical sales spreadsheets",
                    "problem": "Inaccurate projections leading to budget deficits or excessive labor scheduling",
                    "evidence": "Financial management requires forecasting revenue over the coming year based on consumer shifts and promotions."
                },
                {
                    "name": "Bank Drawer Reconciliation & Bookkeeping",
                    "role": "Store Manager / Accountant",
                    "system": "Excel sheets & Accounting portal",
                    "problem": "Manual till reconciliation discrepancies, late filing risks, and high accounting costs",
                    "evidence": "Daily financial updates on sales, refunds, lost inventory, and payroll must be manually reconciled with bank deposits."
                }
            ]
        }
    ]

    count = 0
    for p_data in retail_processes:
        process = models.Process(
            industry="Retail",
            name=p_data["name"],
            created_at=datetime.utcnow()
        )
        db.add(process)
        db.flush()  # Populates process.id
        
        for act_data in p_data["activities"]:
            activity = models.CurrentActivity(
                process_id=process.id,
                name=act_data["name"],
                role=act_data["role"],
                system=act_data["system"],
                problem=act_data["problem"],
                evidence=act_data["evidence"],
                created_at=datetime.utcnow()
            )
            db.add(activity)
            count += 1
            
    db.commit()
    logger.info(f"Successfully seeded {len(retail_processes)} retail processes and {count} current activities.")
    return count
