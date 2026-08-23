import logging
from typing import List, Dict, Any
from backend.app.search.base import BaseSearchProvider

logger = logging.getLogger(__name__)

class MockSearchProvider(BaseSearchProvider):
    def __init__(self):
        self.database = [
            {
                "keywords": ["inventory", "stock", "warehouse", "rfid", "count", "replenish"],
                "results": [
                    {
                        "title": "Shopify Retail Inventory Operations Guide",
                        "url": "https://www.shopify.com/blog/retail-operations",
                        "snippet": "Syncing real-time inventory data across channels prevents stockouts and overstocking. Automating purchase orders based on low-stock alerts and using RFID scanners eliminates physical count discrepancies."
                    },
                    {
                        "title": "McKinsey: Retail Supply Chain Demand Forecasting",
                        "url": "https://www.mckinsey.com/industries/retail/our-insights",
                        "snippet": "AI-driven demand forecasting algorithms analyze historical sales, seasonality, local event context, and weather to optimize warehouse allocations, reducing carrying costs by 30%."
                    },
                    {
                        "title": "ShipBob: 3PL Retail Order Fulfillment Optimization",
                        "url": "https://www.shipbob.com/blog/retail-fulfillment",
                        "snippet": "Splitting inventory across multiple strategically-located fulfillment centers reduces shipping zone distances, leading to lower overall shipping costs and consistent 2-day delivery times."
                    }
                ]
            },
            {
                "keywords": ["customer", "checkout", "loyalty", "queue", "pos", "reward", "bopis", "return"],
                "results": [
                    {
                        "title": "Shopify POS and Checkout Optimization",
                        "url": "https://www.shopify.com/blog/retail-operations",
                        "snippet": "Implementing mobile POS checkouts allows associates to process payments anywhere on the store floor, reducing cashier line lengths and checkout wait times."
                    },
                    {
                        "title": "Yotpo: Retail Customer Loyalty and Rewards",
                        "url": "https://www.yotpo.com/blog/customer-loyalty",
                        "snippet": "Integrating loyalty balances directly with the active POS interface lets cashiers view points and apply discounts in one click, eliminating extra screens and checkout delays."
                    },
                    {
                        "title": "Gartner: Omnichannel Fulfillment and Hybrid Retail Returns",
                        "url": "https://www.gartner.com/en/newsroom/press-releases",
                        "snippet": "Providing a unified online-in-store return portal (BORIS) allows customers to self-register returns, speeding up refunds and restocking times, reducing friction for staff."
                    }
                ]
            },
            {
                "keywords": ["schedule", "onboard", "shift", "train", "employee", "roster", "payroll"],
                "results": [
                    {
                        "title": "Homebase: Automated Scheduling and Clock-In",
                        "url": "https://joinhomebase.com/blog/employee-scheduling",
                        "snippet": "Automating shift scheduler rosters and payroll hours calculations from active clock-in data saves store managers up to 5 hours of administrative work weekly."
                    },
                    {
                        "title": "EasyTeam: Retail POS Staff Management",
                        "url": "https://easyteam.co/blog/staff-scheduling",
                        "snippet": "Integrated staff management software on the POS allows employees to swap shifts and view commissions directly, boosting morale and reducing employee turnover."
                    }
                ]
            },
            {
                "keywords": ["safety", "security", "audit", "compliance", "theft", "shrinkage", "checklist"],
                "results": [
                    {
                        "title": "GoAudits: Digital Store Compliance Audits",
                        "url": "https://goaudits.com/blog/retail-store-audits",
                        "snippet": "Digitizing store opening, closing, and safety checklists provides real-time multi-location compliance visibility and automatically assigns corrective actions to team members."
                    },
                    {
                        "title": "Loss Prevention and CCTV AI Monitoring",
                        "url": "https://www.shopify.com/blog/retail-operations",
                        "snippet": "Using smart AI cameras detects suspicious behavior, alerts employees to hazards like wet floors, and ensures consistent adherence to safety guidelines."
                    }
                ]
            },
            {
                "keywords": ["finance", "forecast", "reconcile", "budget", "bookkeeping", "invoice"],
                "results": [
                    {
                        "title": "Gartner: Automated Financial Reconciliation in Retail",
                        "url": "https://www.gartner.com/en/newsroom/press-releases",
                        "snippet": "Automated ledger systems sync sales reports, payroll data, and banking deposits to reconcile accounts, reducing discrepancies and audit risks."
                    },
                    {
                        "title": "Demand Forecasting and Open-To-Buy Budgeting",
                        "url": "https://www.shopify.com/blog/retail-operations",
                        "snippet": "Advanced AI tools align financial budgeting and open-to-buy plans with forecast demand, reducing obsolete inventory markdowns."
                    }
                ]
            }
        ]

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        logger.info(f"Mock Search falling back for query: '{query}'")
        q_lower = query.lower()
        matched_results = []
        
        # Look for matching category keywords
        for entry in self.database:
            for kw in entry["keywords"]:
                if kw in q_lower:
                    matched_results.extend(entry["results"])
                    break
        
        # If no keywords match, return a general default set of real URLs
        if not matched_results:
            matched_results = [
                {
                    "title": "Shopify Retail Operations Guide",
                    "url": "https://www.shopify.com/blog/retail-operations",
                    "snippet": "Successful retail store operations rely on digital integration of inventory, checkout, scheduling, and loss prevention checks to maximize margins."
                },
                {
                    "title": "McKinsey: Tech-Enabled Transformation in Business Processes",
                    "url": "https://www.mckinsey.com/industries/retail/our-insights",
                    "snippet": "Transforming legacy business processes using digital workflows and automated decision frameworks increases throughput and reduces operational errors."
                }
            ]
            
        # De-duplicate
        unique_results = []
        seen_urls = set()
        for r in matched_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)
                
        return unique_results[:limit]
