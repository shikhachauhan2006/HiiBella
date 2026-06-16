# action/actions.py
# All Rasa custom actions + MySQL queries — all in one file

import pymysql
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

# ── DB Config ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "shikha142",      # ← change this
    "database": "project_marketplace",
    "charset":  "utf8mb4",
}

def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


# ── Action 1: Search Projects ──────────────────────────────────────────────────
class ActionSearchProjects(Action):
    """
    Triggered when user says:
      'show me python projects' / 'find java projects' / 'browse AI/ML projects'
    Reads the 'category' slot set by NLU entity extraction.
    """

    def name(self) -> Text:
        return "action_search_projects"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Map common user phrases → DB category slugs
        CATEGORY_MAP = {
            "java":         "java",
            "python":       "python",
            "ai":           "ai-ml",
            "ai/ml":        "ai-ml",
            "machine learning": "ai-ml",
            "ml":           "ai-ml",
            "web":          "web-dev",
            "web dev":      "web-dev",
            "web development": "web-dev",
            "final year":   "final-year",
            "final":        "final-year",
            "mini":         "mini",
        }

        raw_category = tracker.get_slot("category")
        slug = CATEGORY_MAP.get(raw_category.lower(), None) if raw_category else None

        try:
            db  = get_db()
            cur = db.cursor()

            if slug:
                cur.execute(
                    """
                    SELECT p.title, p.price, p.tech_stack, p.difficulty
                    FROM   projects p
                    JOIN   categories c ON c.id = p.category_id
                    WHERE  c.slug = %s AND p.status = 'approved'
                    ORDER  BY p.is_featured DESC, p.total_sales DESC
                    LIMIT  5
                    """,
                    (slug,)
                )
            else:
                cur.execute(
                    """
                    SELECT p.title, p.price, p.tech_stack, p.difficulty
                    FROM   projects p
                    WHERE  p.status = 'approved'
                    ORDER  BY p.is_featured DESC, p.total_sales DESC
                    LIMIT  5
                    """
                )
            rows = cur.fetchall()

            if rows:
                label = raw_category.title() if raw_category else "Available"
                msg   = f"Here are some {label} projects:\n\n"
                for i, r in enumerate(rows, 1):
                    msg += (
                        f"{i}. 📁 *{r['title']}*\n"
                        f"   💰 Price: ₹{r['price']}  |  🔧 {r['tech_stack']}\n"
                        f"   📊 Level: {r['difficulty'].title()}\n\n"
                    )
                msg += "Type the project name for more details, or 'buy' to purchase!"
            else:
                msg = (
                    f"Sorry, no {raw_category or ''} projects are available right now. "
                    "We're adding new ones daily! Check back soon or try another category."
                )

            dispatcher.utter_message(text=msg)

        except Exception as e:
            dispatcher.utter_message(
                text="Sorry, I couldn't fetch projects right now. Please try again in a moment."
            )
            print(f"[ActionSearchProjects] DB error: {e}")
        finally:
            db.close()

        return []


# ── Action 2: Get Project Details ──────────────────────────────────────────────
class ActionGetProjectDetails(Action):
    """
    Triggered when user asks for details about a specific project.
    Uses the 'project_name' slot.
    """

    def name(self) -> Text:
        return "action_get_project_details"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        project_name = tracker.get_slot("project_name")
        if not project_name:
            dispatcher.utter_message(
                text="Which project would you like details about? Please mention the project name."
            )
            return []

        try:
            db  = get_db()
            cur = db.cursor()
            cur.execute(
                """
                SELECT p.title, p.description, p.price, p.tech_stack,
                       p.difficulty, p.avg_rating, p.total_sales,
                       c.name AS category, p.demo_url
                FROM   projects p
                JOIN   categories c ON c.id = p.category_id
                WHERE  p.status = 'approved'
                  AND  p.title LIKE %s
                LIMIT  1
                """,
                (f"%{project_name}%",)
            )
            row = cur.fetchone()

            if row:
                stars = "⭐" * round(row["avg_rating"])
                msg   = (
                    f"📁 *{row['title']}*\n"
                    f"📂 Category: {row['category']}\n"
                    f"💰 Price: ₹{row['price']}\n"
                    f"🔧 Tech: {row['tech_stack']}\n"
                    f"📊 Level: {row['difficulty'].title()}\n"
                    f"⭐ Rating: {stars} ({row['avg_rating']}/5)\n"
                    f"🛒 Sold: {row['total_sales']} times\n\n"
                    f"📝 {row['description']}\n\n"
                )
                if row["demo_url"]:
                    msg += f"🔗 Demo: {row['demo_url']}\n\n"
                msg += "Type 'buy' to purchase this project!"
            else:
                msg = (
                    f"I couldn't find a project matching '{project_name}'. "
                    "Try browsing by category — type 'show python projects' for example."
                )

            dispatcher.utter_message(text=msg)

        except Exception as e:
            dispatcher.utter_message(
                text="Couldn't fetch project details right now. Please try again."
            )
            print(f"[ActionGetProjectDetails] DB error: {e}")
        finally:
            db.close()

        return []


# ── Action 3: Check Order Status ───────────────────────────────────────────────
class ActionCheckOrderStatus(Action):
    """
    Triggered when buyer asks: 'where is my order' / 'check my order ORD123'
    Uses the 'order_id' or 'email' slot.
    """

    def name(self) -> Text:
        return "action_check_order_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        order_id = tracker.get_slot("order_id")
        email    = tracker.get_slot("email")

        if not order_id and not email:
            dispatcher.utter_message(
                text=(
                    "To check your order, please provide:\n"
                    "• Your **Order ID** (e.g. ORD-1234), or\n"
                    "• Your registered **email address**"
                )
            )
            return []

        try:
            db  = get_db()
            cur = db.cursor()

            if order_id:
                cur.execute(
                    """
                    SELECT o.id, p.title, o.status, o.amount_paid, o.purchased_at
                    FROM   orders o
                    JOIN   projects p ON p.id = o.project_id
                    WHERE  o.id = %s
                    LIMIT  1
                    """,
                    (order_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT o.id, p.title, o.status, o.amount_paid, o.purchased_at
                    FROM   orders o
                    JOIN   projects p ON p.id = o.project_id
                    JOIN   users u    ON u.id = o.buyer_id
                    WHERE  u.email = %s
                    ORDER  BY o.created_at DESC
                    LIMIT  3
                    """,
                    (email,)
                )

            rows = cur.fetchall()

            STATUS_EMOJI = {
                "completed": "✅",
                "pending":   "⏳",
                "failed":    "❌",
                "refunded":  "🔄",
            }

            if rows:
                msg = "Here are your recent orders:\n\n"
                for r in rows:
                    emoji = STATUS_EMOJI.get(r["status"], "📦")
                    msg  += (
                        f"{emoji} Order #{r['id']}\n"
                        f"   📁 {r['title']}\n"
                        f"   💰 ₹{r['amount_paid']}\n"
                        f"   📌 Status: {r['status'].upper()}\n\n"
                    )
                if any(r["status"] == "completed" for r in rows):
                    msg += "✅ For completed orders, go to **My Orders → Download** to get your files."
            else:
                msg = (
                    "No orders found. Please double-check your Order ID or email address.\n"
                    "Need help? Type 'contact support'."
                )

            dispatcher.utter_message(text=msg)

        except Exception as e:
            dispatcher.utter_message(
                text="Couldn't fetch your order right now. Please try again or contact support."
            )
            print(f"[ActionCheckOrderStatus] DB error: {e}")
        finally:
            db.close()

        return []


# ── Action 4: Check Seller Approval Status ─────────────────────────────────────
class ActionCheckApprovalStatus(Action):
    """
    Triggered when seller asks: 'has my project been approved?'
    Uses the 'email' slot.
    """

    def name(self) -> Text:
        return "action_check_approval_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        email = tracker.get_slot("email")

        if not email:
            dispatcher.utter_message(
                text="Please provide your registered seller email to check your project approval status."
            )
            return []

        try:
            db  = get_db()
            cur = db.cursor()
            cur.execute(
                """
                SELECT p.title, p.status, p.created_at
                FROM   projects p
                JOIN   users u ON u.id = p.seller_id
                WHERE  u.email = %s
                ORDER  BY p.created_at DESC
                LIMIT  5
                """,
                (email,)
            )
            rows = cur.fetchall()

            STATUS_EMOJI = {
                "approved": "✅",
                "pending":  "⏳",
                "rejected": "❌",
                "draft":    "📝",
            }

            if rows:
                msg = "Here are your submitted projects:\n\n"
                for r in rows:
                    emoji = STATUS_EMOJI.get(r["status"], "📁")
                    msg  += (
                        f"{emoji} *{r['title']}*\n"
                        f"   Status: **{r['status'].upper()}**\n\n"
                    )
                msg += (
                    "⏳ Pending projects are reviewed within 24 hours.\n"
                    "❌ Rejected? Type 'contact support' to find out why."
                )
            else:
                msg = (
                    f"No projects found for {email}.\n"
                    "Make sure you're using your registered seller email."
                )

            dispatcher.utter_message(text=msg)

        except Exception as e:
            dispatcher.utter_message(
                text="Couldn't fetch approval status right now. Please try again."
            )
            print(f"[ActionCheckApprovalStatus] DB error: {e}")
        finally:
            db.close()

        return []
