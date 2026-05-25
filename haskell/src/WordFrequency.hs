module WordFrequency where

import Data.Char (isAlphaNum, toLower)
import Data.List (sortOn)
import Data.Ord (Down (..))
import qualified Data.Map.Strict as Map

text :: String
text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

main :: IO ()
main = mapM_ (\(w, c) -> putStrLn (w ++ ": " ++ show c)) top
  where
    norm c = if isAlphaNum c then toLower c else ' '
    tokens = words (map norm text)
    counts = Map.fromListWith (+) [(w, 1 :: Int) | w <- tokens]
    top = take 5 (sortOn (\(w, c) -> (Down c, w)) (Map.toList counts))
