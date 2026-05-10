use axum::{
    Json, Router,
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, sync::Arc};
use tokio::sync::Mutex;

#[derive(Clone, Serialize)]
struct User {
    id: u64,
    name: String,
}

#[derive(Deserialize)]
struct NewUser {
    name: String,
}

type Store = Arc<Mutex<HashMap<u64, User>>>;

async fn list_users(State(store): State<Store>) -> Json<Vec<User>> {
    let users = store.lock().await.values().cloned().collect();
    Json(users)
}

async fn get_user(State(store): State<Store>, Path(id): Path<u64>) -> Result<Json<User>, StatusCode> {
    store
        .lock()
        .await
        .get(&id)
        .cloned()
        .map(Json)
        .ok_or(StatusCode::NOT_FOUND)
}

async fn create_user(State(store): State<Store>, Json(input): Json<NewUser>) -> Json<User> {
    let mut users = store.lock().await;
    let id = users.len() as u64 + 1;
    let user = User { id, name: input.name };
    users.insert(id, user.clone());
    Json(user)
}

#[tokio::main]
async fn main() {
    let store = Arc::new(Mutex::new(HashMap::new()));
    let app = Router::new()
        .route("/users", get(list_users).post(create_user))
        .route("/users/{id}", get(get_user))
        .with_state(store);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
