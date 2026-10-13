import copy
from pathlib import Path
import tempfile
import unittest

import import_schedule as imp


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.manifest = imp.read_manifest(Path(__file__).with_name('fall-2026-import.json'))
        self.manifest['items'] = [copy.deepcopy(self.manifest['items'][0])]
        self.source = self.manifest['items'][0]
        self.fields = []
        for name, kind in imp.FIELD_TYPES.items():
            field = dict(id='field-' + name, name=name, dataType=kind)
            if kind == 'SINGLE_SELECT':
                values = ['Todo', 'In Progress', 'Done'] if name == 'Status' else list(imp.PHASES.values())
                field['options'] = [dict(id='option-' + v, name=v) for v in values]
            self.fields.append(field)
        self.issue = dict(id='issue-1', number=1, url=self.source['issue_url'],
                          title=self.source['title'], body=imp.issue_body(self.source),
                          state='OPEN', assignees={'nodes': [{'login': self.source['assignee']}]})
        values = []
        for name, value in imp.desired_fields(self.source, self.manifest).items():
            if value is not None:
                kind = {'TEXT': 'text', 'DATE': 'date', 'SINGLE_SELECT': 'name'}[imp.FIELD_TYPES[name]]
                values.append({kind: value, 'field': {'name': name}})
        self.pitem = dict(id='item-1', content={'id': 'issue-1'},
                          fieldValues={'nodes': values, 'pageInfo': {'hasNextPage': False}})
        self.state = dict(fields=self.fields, users=[dict(login=self.source['assignee'], id='user-1')],
                          issues=[self.issue], items=[self.pitem],
                          repository={'id': 'repo-1'}, project={'id': 'project-1'})

    def test_existing_progress_is_skipped(self):
        self.issue['title'] = 'Team revised title'
        self.pitem['fieldValues']['nodes'][0]['name'] = 'Todo'
        plan, _ = imp.make_plan(self.manifest, self.state)
        self.assertEqual(plan[0]['action'], 'SKIP existing')

    def test_matching_update_has_no_writes(self):
        plan, fields = imp.make_plan(self.manifest, self.state, True)
        self.assertEqual(plan[0]['action'], 'UNCHANGED')
        class NoWrites:
            def query(self, *args, **kwargs):
                raise AssertionError('Unexpected mutation')
        with tempfile.TemporaryDirectory() as folder:
            imp.apply_plan(NoWrites(), self.manifest, self.state, plan, fields, Path(folder) / 'results.json')

    def test_duplicate_marker_stops(self):
        self.state['issues'].append(copy.deepcopy(self.issue))
        with self.assertRaisesRegex(ValueError, 'Multiple issues'):
            imp.make_plan(self.manifest, self.state)

    def test_recorded_url_cannot_point_elsewhere(self):
        self.source['issue_url'] += '9'
        with self.assertRaisesRegex(ValueError, 'Recorded issue URL'):
            imp.make_plan(self.manifest, self.state)

    def test_missing_field_or_assignee_stops_preflight(self):
        for change in ['field', 'user']:
            state = copy.deepcopy(self.state)
            if change == 'field':
                state['fields'] = state['fields'][1:]
            else:
                state['users'] = []
            with self.assertRaises(ValueError):
                imp.make_plan(self.manifest, state)

    def test_resume_attaches_existing_issue_without_creation(self):
        self.state['items'] = []
        plan, fields = imp.make_plan(self.manifest, self.state, True)
        calls = []
        class FakeAPI:
            def query(self, query, **variables):
                calls.append(query)
                if 'addProjectV2ItemById' in query:
                    return {'addProjectV2ItemById': {'item': {'id': 'item-1'}}}
                return {}
        with tempfile.TemporaryDirectory() as folder:
            records = imp.apply_plan(FakeAPI(), self.manifest, self.state, plan, fields, Path(folder) / 'results.json')
        self.assertFalse(any('createIssue' in q for q in calls))
        self.assertTrue(records[0]['complete'])
        self.assertTrue(any('addProjectV2ItemById' in q for q in calls))

    def test_null_target_clears_only_on_explicit_update(self):
        self.pitem['fieldValues']['nodes'].append({'date': '2026-09-14', 'field': {'name': 'Target date'}})
        plan, _ = imp.make_plan(self.manifest, self.state, True)
        self.assertIsNone(plan[0]['fields']['Target date'])
        self.assertEqual(plan[0]['action'], 'UPDATE')

    def test_pagination_follows_cursor(self):
        cursors = []
        class FakeAPI:
            def query(self, query, **variables):
                cursors.append(variables['cursor'])
                return {'nodes': [len(cursors)], 'pageInfo': {'hasNextPage': len(cursors) == 1, 'endCursor': 'second'}}
        self.assertEqual(list(imp.pages(FakeAPI(), '', {}, lambda x: x)), [1, 2])
        self.assertEqual(cursors, [None, 'second'])


if __name__ == '__main__':
    unittest.main()
