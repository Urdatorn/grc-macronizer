local export = {}

local anchor_encode = mw.uri.anchorEncode
local concat = table.concat
local insert = table.insert
local language_anchor -- Defined below.

function export.language_anchor(lang, id)
	return anchor_encode(lang:getFullName() .. ": " .. id)
end
language_anchor = export.language_anchor

function export.make_anchors(ids)
	local anchors = {}
	for i = 1, #ids do
		insert(anchors, "<span class=\"template-anchor\" id=\"" .. anchor_encode(ids[i]) .. "\"></span>")
	end
	return concat(anchors)
end

function export.senseid(lang, id, tag_name)
	-- The following tag is opened but never closed, where is it supposed to be closed?
	--         with <li> it doesn't matter, as it is closed automatically.
	--         with <p> it is a problem
	
	return "<" .. tag_name .. " class=\"senseid\" id=\"" .. language_anchor(lang, id) .. "\">"
end

function export.etymid(lang, id)
	return "<span class=\"etymid\" id=\"" .. language_anchor(lang, id) .. "\"></span>"
end


return export