"""Import reviewed schedule JSON into an organization Project. Preview is default.

Python 3.10+, standard library only. Credentials come exclusively from GH_TOKEN.
Existing issues are skipped unless --update-existing is explicitly supplied.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PHASES = {
    "1": "1. Requirements", "2": "2. Concepts and prototype",
    "3": "3. Detailed design", "4": "4. Release review",
}
FIELD_TYPES = {"Status": "SINGLE_SELECT", "Phase": "SINGLE_SELECT",
               "Duration": "TEXT", "Schedule ID": "TEXT",
               "Start week": "DATE", "Final week": "DATE", "Target date": "DATE"}


def read_manifest(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", data.get("repository", "")):
        raise ValueError("repository must be owner/repository")
    if not isinstance(data.get("project_number"), int) or data["project_number"] < 1:
        raise ValueError("project_number must be a positive integer")
    if not data.get("project_title") or not data.get("items"):
        raise ValueError("project_title and nonempty items are required")
    keys, ids = set(), set()
    for item in data["items"]:
        for name in ("schedule_id", "import_key", "title", "body", "assignee", "duration", "status_proposal"):
            if not isinstance(item.get(name), str) or not item[name].strip():
                raise ValueError(f"Each item requires a nonempty {name}")
        key, sid = item["import_key"], item["schedule_id"]
        if key in keys or sid in ids:
            raise ValueError(f"Duplicate import key or schedule ID: {sid}")
        if not re.fullmatch(r"[A-Za-z0-9:._-]+", key):
            raise ValueError(f"Invalid import key: {key}")
        keys.add(key)
        ids.add(sid)
        for name in ("start_week", "final_week", "suggested_target_date"):
            value = item.get(name)
            if value and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) or dt.date.fromisoformat(value).isoformat() != value):
                raise ValueError(f"Invalid {name} for {sid}")
        if item.get("start_week") and item.get("final_week") and item["start_week"] > item["final_week"]:
            raise ValueError(f"Start week follows final week: {sid}")
    return data


def desired_fields(item, manifest):
    phase = item.get("project_phase") or manifest.get("phase_options", PHASES).get(item["schedule_id"].split(".")[0])
    if not phase:
        raise ValueError(f"Specify project_phase or phase_options for {item['schedule_id']}")
    return {"Status": item["status_proposal"], "Phase": phase,
            "Duration": item["duration"], "Schedule ID": item["schedule_id"],
            "Start week": item.get("start_week"), "Final week": item.get("final_week"),
            "Target date": item.get("suggested_target_date")}


def issue_body(item):
    marker = f"<!-- {item['import_key']} -->"
    return item["body"] if marker in item["body"] else item["body"].rstrip() + "\n\n" + marker


class GitHub:
    def __init__(self, token):
        self.token = token

    def query(self, query, **variables):
        payload = json.dumps({"query": query, "variables": variables}).encode()
        request = Request("https://api.github.com/graphql", data=payload, headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
            "Accept": "application/vnd.github+json", "User-Agent": "snow-viz-schedule-importer"})
        try:
            with urlopen(request, timeout=60) as response:
                result = json.load(response)
        except HTTPError as error:
            # Never print request headers, tokens, or raw transport exception details.
            raise RuntimeError(f"GitHub HTTP {error.code}. Check token approval, expiry, Issues and Projects permissions.") from None
        except (URLError, TimeoutError):
            raise RuntimeError("GitHub connection failed. A write may have completed; rerun preview before retrying.") from None
        if result.get("errors"):
            messages = "; ".join(e.get("message", "GraphQL error") for e in result["errors"])
            raise RuntimeError(messages.replace(self.token, "[REDACTED]"))
        return result["data"]


FIELD_FRAGMENT = """... on ProjectV2FieldCommon { id name dataType }
... on ProjectV2SingleSelectField { options { id name } }"""
ITEM_FRAGMENT = """id content { ... on Issue { id url } }
fieldValues(first:100) { pageInfo { hasNextPage } nodes {
 ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon { name } } }
 ... on ProjectV2ItemFieldDateValue { date field { ... on ProjectV2FieldCommon { name } } }
 ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name } } }
} }"""


def pages(api, query, variables, connection):
    cursor = None
    while True:
        data = api.query(query, **variables, cursor=cursor)
        page = connection(data)
        yield from page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]


def snapshot(api, manifest):
    owner, repo = manifest["repository"].split("/")
    data = api.query("""query($owner:String!,$repo:String!,$number:Int!){
      viewer { login }
      repository(owner:$owner,name:$repo){id viewerPermission}
      organization(login:$owner){projectV2(number:$number){id title closed}}
    }""", owner=owner, repo=repo, number=manifest["project_number"])
    project = (data.get("organization") or {}).get("projectV2")
    if not project or not data.get("repository"):
        raise ValueError("Repository or organization Project is inaccessible")
    if project["title"] != manifest["project_title"] or project["closed"]:
        raise ValueError("Project title differs from the manifest, or Project is closed. Review the destination.")
    fields = list(pages(api, "query($id:ID!,$cursor:String){node(id:$id){... on ProjectV2 {fields(first:100,after:$cursor){nodes{" + FIELD_FRAGMENT + "}pageInfo{hasNextPage endCursor}}}}}", {"id": project["id"]}, lambda d: d["node"]["fields"]))
    issues = list(pages(api, """query($owner:String!,$repo:String!,$cursor:String){
      repository(owner:$owner,name:$repo){issues(first:100,after:$cursor){
        nodes{id number url title body state assignees(first:100){nodes{login}}}
        pageInfo{hasNextPage endCursor}}}}""", {"owner": owner, "repo": repo}, lambda d: d["repository"]["issues"]))
    users = list(pages(api, """query($owner:String!,$repo:String!,$cursor:String){
      repository(owner:$owner,name:$repo){assignableUsers(first:100,after:$cursor){
        nodes{id login} pageInfo{hasNextPage endCursor}}}}""", {"owner": owner, "repo": repo}, lambda d: d["repository"]["assignableUsers"]))
    items = list(pages(api, "query($id:ID!,$cursor:String){node(id:$id){... on ProjectV2{items(first:100,after:$cursor){nodes{" + ITEM_FRAGMENT + "}pageInfo{hasNextPage endCursor}}}}}", {"id": project["id"]}, lambda d: d["node"]["items"]))
    for item in items:
        if item["fieldValues"]["pageInfo"]["hasNextPage"]:
            raise ValueError("An item has over 100 field values; cannot safely compare it")
    return dict(project=project, repository=data["repository"], login=data["viewer"]["login"],
                fields=fields, issues=issues, users=users, items=items)


def make_plan(manifest, state, update_existing=False):
    fields = {f["name"]: f for f in state["fields"]}
    users = {u["login"].lower(): u["id"] for u in state["users"]}
    project_items = {}
    for pitem in state["items"]:
        if pitem.get("content") and pitem["content"].get("id"):
            project_items.setdefault(pitem["content"]["id"], []).append(pitem)
    plan = []
    for item in manifest["items"]:
        desired = desired_fields(item, manifest)
        for name, value in desired.items():
            if name not in fields or fields[name]["dataType"] != FIELD_TYPES[name]:
                raise ValueError(f"Create Project field {name!r} with type {FIELD_TYPES[name]} first")
            if FIELD_TYPES[name] == "SINGLE_SELECT" and value not in {o["name"] for o in fields[name]["options"]}:
                raise ValueError(f"Missing {name} option {value!r}")
        if item["assignee"].lower() not in users:
            raise ValueError(f"Assignee is not assignable in this repository: {item['assignee']}")
        marker = f"<!-- {item['import_key']} -->"
        matches = [issue for issue in state["issues"] if marker in (issue["body"] or "")]
        if len(matches) > 1:
            raise ValueError(f"Multiple issues contain {item['import_key']}; resolve duplicates first")
        issue = matches[0] if matches else None
        if item.get("issue_url") and (not issue or issue["url"] != item["issue_url"]):
            raise ValueError(f"Recorded issue URL does not match its import marker: {item['schedule_id']}")
        memberships = project_items.get(issue["id"], []) if issue else []
        if len(memberships) > 1:
            raise ValueError(f"Duplicate Project memberships: {item['schedule_id']}")
        pitem = memberships[0] if memberships else None
        current = {}
        if pitem:
            for value in pitem["fieldValues"]["nodes"]:
                if value.get("field"):
                    current[value["field"]["name"]] = value.get("text", value.get("date", value.get("name")))
        changes = {name: value for name, value in desired.items() if current.get(name) != value}
        skip = bool(issue and not update_existing)
        issue_changes = bool(issue and (issue["title"] != item["title"] or issue["body"] != issue_body(item)
                           or {a["login"].lower() for a in issue["assignees"]["nodes"]} != {item["assignee"].lower()}))
        plan.append(dict(source=item, issue=issue, project_item=pitem, fields=changes,
                         user_id=users[item["assignee"].lower()], issue_changes=issue_changes,
                         action="SKIP existing" if skip else "CREATE" if not issue else "UPDATE" if issue_changes or changes or not pitem else "UNCHANGED"))
    return plan, fields


def save_results(path, records):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def apply_plan(api, manifest, state, plan, fields, results_path):
    records = []
    for row in plan:
        source, issue = row["source"], row["issue"]
        if row["action"] in ("SKIP existing", "UNCHANGED"):
            records.append({"import_key": source["import_key"], "issue_url": issue["url"], "action": row["action"]})
            save_results(results_path, records)
            continue
        if not issue:
            issue = api.query("""mutation($input:CreateIssueInput!){createIssue(input:$input){issue{id url}}}""",
                              input={"repositoryId": state["repository"]["id"], "title": source["title"],
                                     "body": issue_body(source), "assigneeIds": [row["user_id"]]})["createIssue"]["issue"]
        elif row["issue_changes"]:
            api.query("mutation($input:UpdateIssueInput!){updateIssue(input:$input){issue{id}}}",
                      input={"id": issue["id"], "title": source["title"], "body": issue_body(source), "assigneeIds": [row["user_id"]]})
        record = {"import_key": source["import_key"], "issue_url": issue["url"], "action": row["action"], "complete": False}
        records.append(record)
        save_results(results_path, records)
        pitem = row["project_item"]
        if not pitem:
            pitem = api.query("mutation($input:AddProjectV2ItemByIdInput!){addProjectV2ItemById(input:$input){item{id}}}",
                              input={"projectId": state["project"]["id"], "contentId": issue["id"]})["addProjectV2ItemById"]["item"]
        record["project_item_id"] = pitem["id"]
        save_results(results_path, records)
        for name, value in row["fields"].items():
            args = {"projectId": state["project"]["id"], "itemId": pitem["id"], "fieldId": fields[name]["id"]}
            if value is None:
                api.query("mutation($input:ClearProjectV2ItemFieldValueInput!){clearProjectV2ItemFieldValue(input:$input){projectV2Item{id}}}", input=args)
            else:
                kind = {"TEXT": "text", "DATE": "date", "SINGLE_SELECT": "singleSelectOptionId"}[FIELD_TYPES[name]]
                if kind == "singleSelectOptionId":
                    value = next(o["id"] for o in fields[name]["options"] if o["name"] == value)
                api.query("mutation($input:UpdateProjectV2ItemFieldValueInput!){updateProjectV2ItemFieldValue(input:$input){projectV2Item{id}}}", input={**args, "value": {kind: value}})
        record["complete"] = True
        save_results(results_path, records)
        print(f"Imported {source['schedule_id']}: {issue['url']}")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--offline", action="store_true", help="Validate JSON without contacting GitHub")
    parser.add_argument("--apply", action="store_true", help="Write the displayed plan to GitHub")
    parser.add_argument("--update-existing", action="store_true", help="Replace matching issue titles, bodies, sole assignees and mapped fields")
    args = parser.parse_args()
    manifest = read_manifest(args.manifest)
    for item in manifest["items"]:
        desired_fields(item, manifest)
    if args.offline:
        if args.apply:
            raise ValueError("--offline cannot be combined with --apply")
        print(f"Validated {len(manifest['items'])} tasks. No GitHub access or changes.")
        return
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("Set GH_TOKEN in this terminal before running the importer")
    api = GitHub(token)
    state = snapshot(api, manifest)
    plan, fields = make_plan(manifest, state, args.update_existing)
    print(f"Account: {state['login']} | Repository: {manifest['repository']} | Project: {state['project']['title']}")
    for row in plan:
        print(f"{row['source']['schedule_id']:6} {row['action']:14} {row['source']['title']}")
    if not args.apply:
        print("PREVIEW ONLY: no changes. Re-run with --apply after reviewing this plan.")
        return
    if state["repository"]["viewerPermission"] not in ("ADMIN", "MAINTAIN", "WRITE"):
        raise ValueError("Your account lacks repository write access")
    print("Project workflows can change issue state when Status changes. Review them first.")
    results_path = args.manifest.with_name(args.manifest.stem + ".results.json")
    records = apply_plan(api, manifest, state, plan, fields, results_path)
    after = snapshot(api, manifest)
    verification, _ = make_plan(manifest, after, True)
    touched = {r["import_key"] for r in records if r["action"] not in ("SKIP existing", "UNCHANGED")}
    pending = [r["source"]["schedule_id"] for r in verification if r["source"]["import_key"] in touched and r["action"] != "UNCHANGED"]
    if pending:
        raise RuntimeError("Saved values differ after import (possibly a workflow): " + ", ".join(pending))
    print(f"Complete. Verified changed items. Results: {results_path}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, KeyError, OSError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        sys.exit(1)
