local m_str_utils = require("string_utilities")

local codepoint = m_str_utils.codepoint
local decode_entities = m_str_utils.decode_entities
local find = string.find
local format = string.format
local gsub = string.gsub
local match = string.match
local pattern_escape = m_str_utils.pattern_escape

local function encode_entity(ch)
	return "&#x" .. format("%X", codepoint(ch)) .. ";"
end

return function(text, charset, raw)
	if not raw then
		text = decode_entities(text)
	end
	if charset == "" then
		return text
	elseif not charset then
		charset = "\"&'<>\194\160"
	elseif not match(charset, "[\128-\244]") then
		return (gsub(text, "[" .. pattern_escape(charset) .. "]", encode_entity))
	end
	return (gsub(text, "[%z\1-\127\194-\244][\128-\191]*", function(ch)
		return find(charset, ch, 1, true) and encode_entity(ch) or nil
	end))
end