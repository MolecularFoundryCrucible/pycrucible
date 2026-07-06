"""Integration tests for client.projects.*"""


def test_project_get(client, project_id):
    p = client.projects.get(project_id)
    assert p is not None
    assert p.get('project_id') == project_id


def test_project_list(client):
    projects = client.projects.list(limit=5)
    assert isinstance(projects, list)
    assert len(projects) > 0


def test_project_search(client):
    results = client.projects.search('test', limit=5)
    assert isinstance(results, list)


def test_project_search_metadata(client):
    results = client.projects.search_metadata('test', limit=5)
    assert isinstance(results, list)
