require("mw")  -- Load the mock MediaWiki functions

local grc_conj = require("grc-conj")

-- Example input for λύω
local input = {
    lemma = "λύω",
    inflection_type = "luō"
}

-- Call the conjugation function
local result = grc_conj.generate(input)

print(result)  -- Display the conjugation table