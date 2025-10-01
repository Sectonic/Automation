import google.generativeai as genai
import json
import os

def init_gemini():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def summarize_emails(emails):
    """
    Input emails: list of dicts with keys:
      from, subject, snippet, link, source
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = """
You are an assistant that organizes emails into clear, useful digests by clustering related emails.
The digest should highlight only the items that truly matter — things the user must act on, know about, or would be glad to see even if they already checked their inbox.

⸻

Goal
	•	Produce only a small number of high-signal groups.
	•	Exclude: spam, promotions, newsletters, optional events, or low-value announcements (e.g. “new product livestream,” “local attractions,” “marketing campaigns”).
	•	Surface only items that:
	•	Require action (deadlines, reviews, sign-ups, responses).
	•	Affect the schedule (meetings, trips, interviews, recruiting sessions).
	•	Are genuinely important to know (results, confirmations of something critical, accepted applications, urgent updates).

⸻

Labels

Pick exactly one per group:
	•	Personal → Friends/family, personal services, purchases, non-school matters.
	•	School → Assignments, class reminders, professors, academic info.
	•	Internships → Recruiters, applications, interviews, career opportunities.
	•	Administrative → Logistics/official matters (bills, banking, IT, subscriptions, housing, government, university).
	•	Projects → Side projects, GitHub, hackathons, collaborations outside coursework.
	•	Social → Clubs, organizations, events, community activities.

⸻

Instructions
	1.	Read the emails (sender, subject, snippet, source, link).
	2.	Form coherent groups by topic (cluster related items together).
    3. In each group’s Summary: 
    - Write in plain text only.
    - Use Markdown links only in the form [anchor](link).
    - Every time you mention a specific email, always include its link.
    - For groups summarizing multiple emails, links are optional unless you call out a particular one.
    - Everything else must stay plain text (no extra Markdown formatting).
    - Prefer one paragraph per group, short and scannable. Split only if absolutely necessary.
    - Do not include low-value items (ads, announcements, optional events, generic “come check this out” emails).
	4.	Keep the digest focused: only what matters, nothing that wastes attention.
	5.	Output must follow this JSON format:

[
  {
    "title": "<Concise Group Title>",
    "label": "<one of: Personal | School | Internships | Administrative | Projects | Social>",
    "summary": "<Plain text summary with Markdown links only for actual actions/resources>"
  }
]
"""

    formatted = "\n\n".join(
        [
            "Email:\n"
            f"From: {e.get('from','')}\n"
            f"Subject: {e.get('subject','')}\n"
            f"Snippet: {e.get('snippet','')}\n"
            f"Source: {e.get('source','')}\n"
            f"Link: {e.get('link','')}"
            for e in emails
        ]
    )

    response = model.generate_content(prompt + f"\n\nEMAILS:\n{formatted}").text.strip()
    
    # Extract JSON from the response (remove markdown code blocks if present)
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0].strip()
    elif "```" in response:
        response = response.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response: {response}")
        # Fallback to empty list if JSON parsing fails
        return []