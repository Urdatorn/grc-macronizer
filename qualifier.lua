local export = {}

local concat = table.concat

function export.wrap_css(text, classes)
	return ("<span class=\"%s\">%s</span>"):format(classes, text)
end

function export.wrap_qualifier_css(text, suffix)
	local css_classes = ("ib-%s qualifier-%s"):format(suffix, suffix)
	return export.wrap_css(text, css_classes)
end

function export.format_qualifiers(list, open, close, opencontent, closecontent, no_ib_content)
	if type(list) ~= "table" then
		list = {list}
	end

	if not list[1] then
		return ""
	end

	local parts = {}
	local function ins(text)
		table.insert(parts, text)
	end

	if open ~= false then
		ins(export.wrap_qualifier_css(open or "(", "brac"))
	end
	if opencontent then
		ins(opencontent)
	end
	local content = concat(list, export.wrap_qualifier_css(",", "comma") .. " ")
	if not no_ib_content then
		content = export.wrap_qualifier_css(content, "content")
	end
	ins(content)
	if closecontent then
		ins(closecontent)
	end
	if close ~= false then
		ins(export.wrap_qualifier_css(close or ")", "brac"))
	end
	return concat(parts)
end

function export.format_qualifier(list, open, close, opencontent, closecontent, no_ib_content)
	return export.format_qualifiers(list, open, close, opencontent, closecontent, no_ib_content)
end

local function format_qualifiers_with_clarification(list, clarification, open, close)
	local opencontent = export.wrap_css(clarification, "qualifier-clarification") ..
		export.wrap_css(open or "“", "qualifier-clarification qualifier-quote")

	local closecontent = export.wrap_css(close or "”", "qualifier-clarification qualifier-quote")

	return export.format_qualifiers(list, "(", ")", opencontent, closecontent)
end

function export.sense(list)
	return export.format_qualifiers(list) .. export.wrap_css(":", "ib-colon sense-qualifier-colon")
end

function export.antsense(list)
	return format_qualifiers_with_clarification(list, "antonym(s) of ") ..
		export.wrap_css(":", "ib-colon sense-qualifier-colon")
end

return export