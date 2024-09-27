## Neo4j commands

### Import the issues_relations.csv file into Neo4j.
Go to Neo4j and go to Issues Relations database, click three dots, Open Folder, Import. Select Issues relations csv. 

### Create Nodes from the CSV
LOAD CSV WITH HEADERS FROM 'file:///issues_relations.csv' AS row
MERGE (issue:Issue {issue_number: row.issue_number})
SET issue.title = row.title;

### Create Relationships Between Issues
LOAD CSV WITH HEADERS FROM 'file:///issues_relations.csv' AS row
WITH row, split(row.related_issues, ",") AS related
UNWIND related AS related_issue
WITH row, trim(related_issue) AS related_issue
WHERE related_issue <> ""  // Skip empty relations
MATCH (src:Issue {issue_number: row.issue_number})
MATCH (dst:Issue {issue_number: related_issue})
MERGE (src)-[:REFERENCES]->(dst);

### Return the Data to Visualize in the Browser
MATCH (i:Issue)-[r:REFERENCES]->(j:Issue)
RETURN i, r, j
