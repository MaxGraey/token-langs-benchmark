package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"sync"
)

type User struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

func main() {
	var mu sync.Mutex
	users := map[int]User{}

	http.HandleFunc("/users", func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		switch r.Method {
		case http.MethodGet:
			list := make([]User, 0, len(users))
			for _, u := range users {
				list = append(list, u)
			}
			json.NewEncoder(w).Encode(list)
		case http.MethodPost:
			var in struct {
				Name string `json:"name"`
			}
			json.NewDecoder(r.Body).Decode(&in)
			u := User{ID: len(users) + 1, Name: in.Name}
			users[u.ID] = u
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(u)
		}
	})

	http.HandleFunc("/users/", func(w http.ResponseWriter, r *http.Request) {
		id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/users/"))
		if err != nil {
			http.NotFound(w, r)
			return
		}
		mu.Lock()
		defer mu.Unlock()
		u, ok := users[id]
		if !ok {
			http.NotFound(w, r)
			return
		}
		json.NewEncoder(w).Encode(u)
	})

	http.ListenAndServe("127.0.0.1:3000", nil)
}
