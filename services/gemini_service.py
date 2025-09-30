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

GOAL
- Produce only a small number of high-signal groups.
- Exclude spam/promotions/irrelevant clutter.

LABELS (pick exactly one per group)
- Personal → Friends/family, personal services, purchases, non-school matters.
- School → Assignments, class reminders, professors, academic info.
- Internships → Recruiters, applications, interviews, career opportunities.
- Administrative → Any logistics/official matters (bills, banking, IT, subscriptions, housing, government, university).
- Projects → Side projects, GitHub, hackathons, collaborations outside coursework.
- Social → Clubs, organizations, events, community activities.

INSTRUCTIONS
1) Read the emails (sender, subject, snippet, source, link).
2) Form coherent groups by topic.
3) In each group's Summary (brief), synthesize meaning and actions; do not restate snippets.
4) When referencing a concrete action or resource from a specific email (e.g., “coding assessment link” or “interview details”),
   create a Markdown link using the provided email's link: [anchor text]({{that email's link}}).
5) Keep the output compact and scannable.

OUTPUT FORMAT (valid JSON only, no extra text):
```json
[
  {
    "title": "<Concise Group Title>",
    "label": "<one of: Personal | School | Internships | Administrative | Projects | Social>",
    "summary": "<brief synthesis with some markdown links to specific emails if applicable>"
  }
]
```
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