(ns http-rest
  (:require [muuntaja.core :as m]
            [reitit.ring :as ring]
            [reitit.ring.middleware.muuntaja :as muuntaja]
            [reitit.ring.middleware.parameters :as parameters]
            [ring.adapter.jetty :as jetty]))

(def store (atom {}))

(defn- list-users [_]
  {:status 200 :body (vals @store)})

(defn- get-user [{{{:keys [id]} :path} :parameters}]
  (if-let [user (@store (parse-long id))]
    {:status 200 :body user}
    {:status 404 :body nil}))

(defn- create-user [{{:keys [body]} :parameters}]
  (let [user (-> (swap! store
                        (fn [s]
                          (let [id (inc (count s))]
                            (assoc s id {:id id :name (:name body)}))))
                 vals
                 last)]
    {:status 201 :body user}))

(def app
  (ring/ring-handler
    (ring/router
      [["/users"     {:get  list-users
                      :post create-user}]
       ["/users/:id" {:get        get-user
                      :parameters {:path {:id string?}}}]]
      {:data {:muuntaja   m/instance
              :middleware [parameters/parameters-middleware
                           muuntaja/format-middleware]}})))

(defn -main [& _]
  (jetty/run-jetty app {:port 3000 :join? false}))
