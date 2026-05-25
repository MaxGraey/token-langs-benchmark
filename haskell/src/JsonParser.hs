{-# LANGUAGE LambdaCase #-}
module JsonParser where

import Control.Applicative (Alternative (..))

data Value
  = JNull
  | JBool Bool
  | JNumber Double
  | JString String
  | JArray [Value]
  | JObject [(String, Value)]
  deriving Show

newtype Parser a = Parser { runP :: String -> Maybe (a, String) }

instance Functor Parser where
  fmap f (Parser p) = Parser (fmap (\(a, s) -> (f a, s)) . p)

instance Applicative Parser where
  pure a = Parser (\s -> Just (a, s))
  Parser pf <*> Parser pa = Parser $ \s -> do
    (f, s1) <- pf s
    (a, s2) <- pa s1
    Just (f a, s2)

instance Monad Parser where
  Parser pa >>= f = Parser $ \s -> do
    (a, s1) <- pa s
    runP (f a) s1

instance Alternative Parser where
  empty = Parser (const Nothing)
  Parser p <|> Parser q = Parser (\s -> p s <|> q s)

satisfy :: (Char -> Bool) -> Parser Char
satisfy ok = Parser $ \case
  (c:rest) | ok c -> Just (c, rest)
  _ -> Nothing

char :: Char -> Parser Char
char c = satisfy (== c)

ws :: Parser ()
ws = Parser (\s -> Just ((), dropWhile (`elem` " \t\n\r") s))

literal :: String -> a -> Parser a
literal word value = mapM_ char word *> pure value

between :: Parser open -> Parser close -> Parser a -> Parser a
between open close p = open *> p <* close

sepBy :: Parser a -> Parser sep -> Parser [a]
sepBy p sep = ((:) <$> p <*> many (sep *> p)) <|> pure []

jString :: Parser String
jString = char '"' *> many jChar <* char '"'
  where
    jChar = (char '\\' *> escaped) <|> satisfy (/= '"')
    escaped = Parser $ \case
      (c:r) | Just d <- lookup c table -> Just (d, r)
      _ -> Nothing
    table = [('"','"'), ('\\','\\'), ('/','/'), ('b','\b'), ('f','\f'), ('n','\n'), ('r','\r'), ('t','\t')]

jNumber :: Parser Double
jNumber = Parser $ \s ->
  let (digits, rest) = span (`elem` "0123456789+-.eE") s
  in if null digits then Nothing else Just (read digits, rest)

value :: Parser Value
value = ws *> v <* ws
  where
    v = literal "null"  JNull
    <|> literal "true"  (JBool True)
    <|> literal "false" (JBool False)
    <|> JString <$> jString
    <|> JNumber <$> jNumber
    <|> JArray  <$> between (char '[') (char ']') (sepBy value (char ','))
    <|> JObject <$> between (char '{') (char '}') (sepBy entry (char ','))
    entry = (,) <$> (ws *> jString <* ws <* char ':') <*> value

main :: IO ()
main = case runP value "{\"name\":\"Ada\",\"scores\":[1,2,3],\"ok\":true}" of
  Just (v, "") -> print v
  _ -> error "parse failure"
