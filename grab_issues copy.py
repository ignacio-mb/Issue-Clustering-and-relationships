import requests
import csv
import re
from collections import defaultdict
import os  # Added to check if a file exists

# Define constants
GITHUB_REPO = "metabase/metabase"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}"
ISSUES_URL = f"{GITHUB_API_URL}/issues"
MAX_ISSUES = 5000  # Set the maximum number of issues to fetch
CSV_FILE = "metabase_issues_filtered.csv"
NEO4J_FILE = "issues_relations.csv"

# Replace with your GitHub token for higher rate limits and authenticated access
GITHUB_TOKEN = "yourtoken"  # Replace with your GitHub token

# Function to fetch the latest issues (excluding PRs) with pagination support
def fetch_latest_issues():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    all_issues = []
    page = 1

    while len(all_issues) < MAX_ISSUES:
        # Fetch issues page-by-page with a limit of 100 per page
        params = {"per_page": 100, "state": "all", "sort": "created", "direction": "desc", "page": page}
        response = requests.get(ISSUES_URL, headers=headers, params=params)
        response.raise_for_status()
        issues = response.json()

        # If no more issues are returned, break out of the loop
        if not issues:
            break

        # Filter out pull requests (they have a "pull_request" key)
        filtered_issues = [issue for issue in issues if "pull_request" not in issue]

        # Add filtered issues to the main list
        all_issues.extend(filtered_issues)
        
        # Move to the next page
        page += 1

    # Return only up to the MAX_ISSUES limit
    return all_issues[:MAX_ISSUES]

# Function to fetch comments for a given issue (excluding system comments)
def fetch_issue_comments(issue_number):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    comments_url = f"{ISSUES_URL}/{issue_number}/comments"
    response = requests.get(comments_url, headers=headers)
    response.raise_for_status()
    comments = response.json()
    return [comment for comment in comments if comment['user']['type'] == "User"]

# Function to parse issue body and comments for issue mentions (ignoring PR references)
def parse_relations(text):
    if not text:
        return ""
    issue_number_references = re.findall(r"(?:#|https://github\.com/metabase/metabase/issues/)(\d+)", text)
    return ", ".join(issue_number_references) if issue_number_references else ""

# Function to prepare the Neo4j CSV file based on the filtered issues CSV
def prepare_neo4j_csv(input_file, output_file):
    issues_data = defaultdict(lambda: {"title": "", "related_issues": set()})

    # Read the existing CSV file
    with open(input_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            issue_number = row["Issue Number"]
            title = row["Issue Title"]
            related_issues = row["Relations"]

            # Add the issue title and relations
            issues_data[issue_number] = {"title": title, "related_issues": set(related_issues.split(", ")) if related_issues else set()}

    # Write to the new CSV file for Neo4j
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["issue_number", "related_issues", "title"])  # CSV headers

        for issue_number, data in issues_data.items():
            # Format related issues as a comma-separated string
            related_issues_str = ", ".join(sorted(data["related_issues"]))
            writer.writerow([issue_number, related_issues_str, data["title"]])

    print(f"Data successfully written to {output_file}")

# Main script to fetch issues and comments, then write to CSV
def main():
    # Step 1: Fetch issues and generate the primary CSV file
    issues = fetch_latest_issues()
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Issue Number", "Issue Title", "Comment ID", "Comment Body", "Comment Author", "Comment Created At", "Relations"])

        for issue in issues:
            issue_number = issue['number']
            issue_title = issue['title']
            issue_body = issue['body'].replace('\n', ' ') if issue['body'] else ""
            issue_author = issue['user']['login']
            issue_created_at = issue['created_at']
            issue_relations = parse_relations(issue_body)
            writer.writerow([issue_number, issue_title, f"issue-{issue_number}", issue_body, issue_author, issue_created_at, issue_relations])

            comments = fetch_issue_comments(issue_number)
            for comment in comments:
                comment_body = comment['body'].replace('\n', ' ')
                comment_author = comment['user']['login']
                comment_relations = parse_relations(comment_body)
                writer.writerow([issue_number, issue_title, comment['id'], comment_body, comment_author, comment['created_at'], comment_relations])

    print(f"Data successfully written to {CSV_FILE}")

    # Step 2: Check if the issues_relations CSV file exists. If not, create it.
    if not os.path.exists(NEO4J_FILE):
        print(f"{NEO4J_FILE} not found. Creating a new one.")
        prepare_neo4j_csv(CSV_FILE, NEO4J_FILE)
    else:
        print(f"{NEO4J_FILE} already exists. Skipping creation.")

if __name__ == "__main__":
    main()

