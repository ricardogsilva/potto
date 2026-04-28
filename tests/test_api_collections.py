def test_api_collection_list(
        db,
        admin_user,
        sample_feature_collection,
        webapp_test_client_as_admin,
):
    response = webapp_test_client_as_admin.get("/api/collections")
    assert response.status_code == 200
    assert response.json()["collections"][0]["id"] == sample_feature_collection.resource_identifier