{-# LANGUAGE OverloadedStrings #-}
module HttpRest where

import Control.Monad.IO.Class (liftIO)
import Data.Aeson (FromJSON, ToJSON, parseJSON, toJSON, object, withObject, (.=), (.:))
import Data.IORef (atomicModifyIORef', newIORef, readIORef)
import qualified Data.Map.Strict as Map
import Network.HTTP.Types.Status (created201, notFound404)
import Web.Scotty (get, json, jsonData, param, post, scotty, status)

data User = User { userId :: Int, userName :: String }

instance ToJSON User where
  toJSON (User i n) = object ["id" .= i, "name" .= n]

newtype NewUser = NewUser String

instance FromJSON NewUser where
  parseJSON = withObject "NewUser" (\o -> NewUser <$> o .: "name")

main :: IO ()
main = do
  store <- newIORef (Map.empty :: Map.Map Int User)
  scotty 3000 $ do
    get "/users" $ do
      users <- liftIO (readIORef store)
      json (Map.elems users)

    get "/users/:id" $ do
      uid <- param "id"
      users <- liftIO (readIORef store)
      maybe (status notFound404) json (Map.lookup uid users)

    post "/users" $ do
      NewUser n <- jsonData
      user <- liftIO $ atomicModifyIORef' store $ \users ->
        let uid = Map.size users + 1
            u = User uid n
         in (Map.insert uid u users, u)
      status created201
      json user
