local export = {}

local rsplit = mw.text.split

--[==[
Parse a references spec as used in the {{para|ref}} param to {{tl|IPA}}, {{tl|IPAchar}}, {{tl|homophones}},
{{tl|rhymes}}, etc. and soon the {{para|f<var>N</var>ref}} param to {{tl|head}}. `parse_err` is a function of one
argument to throw an error with the specified argument as the error message; defaults to `error`.

Multiple references are separated by `!!!` (optionally with spaces around it), and the equivalent of
`<nowiki><ref name="bendo">{{R:it:DiPI|bendo}}</ref><ref>{{R:it:Olivetti}}</ref></nowiki>` can be specified using a
syntax like the following:

{ {{IPA|it|ˈben.do|ˈbɛn.do|ref2={{R:it:DiPI|bendo}}<<name:bendo>> !!! {{R:it:Olivetti}}}}}

To include a group as in `<nowiki><ref name="bendo" group="pron">...</ref></nowiki>` use:

{ {{IPA|it|ˈben.do|ˈbɛn.do|ref2={{R:it:DiPI|bendo}}<<name:bendo>><<group:pron>>}}}

To reference a prior name, as in `<nowiki><ref name="bendo"/></nowiki>`, leave the reference text blank:

{ {{IPA|it|ˈben.do|ˈbɛn.do|ref2=<<name:bendo>>}}}

Similarly, to reference a prior name in a particular group, as in `<nowiki><ref name="bendo" group="pron"/></nowiki>`, use:

{ {{IPA|it|ˈben.do|ˈbɛn.do|ref2=<<name:bendo>><<group:pron>>}}}

The return value consists of a list of objects of the form { {text = TEXT, name = NAME, group = GROUP}}.
This is the same format as is expected in the `part.refs` in [[Module:headword]] and `item.refs` in
[[Module:IPA]].
]==]
function export.parse_references(text, parse_err)
	parse_err = parse_err or error
	local refs = {}
	local raw_notes = rsplit(text, "%s*!!!%s*")
	for _, raw_note in ipairs(raw_notes) do
		local note
		if raw_note:find("<<") then
			local splitvals = require("Module:string utilities").split(raw_note, "(<<[a-z]+:.->>)")
			note = {text = splitvals[1]}
			for i = 2, #splitvals, 2 do
				local key, value = splitvals[i]:match("^<<([a-z]+):(.*)>>$")
				if not key then
					parse_err("Internal error: Can't parse " .. splitvals[i])
				end
				if key == "name" or key == "group" then
					note[key] = value
				else
					parse_err("Unrecognized key '" .. key .. "' in " .. splitvals[i])
				end
				if splitvals[i + 1] ~= "" then
					parse_err("Extraneous text '" .. splitvals[i + 1] .. "' after " .. splitvals[i])
				end
			end
		else
			note = raw_note
		end
		table.insert(refs, note)
	end
	
	return refs
end

--[==[
Format a list of reference specs, using a parser function. The return string contains a footnote number that hyperlinks
to the actual reference, located in the `<nowiki><references /></nowiki>` section. The format an individual reference
spec is either a string containing the reference text (typically a call to a citation template such as {{tl|cite-book}},
or a template wrapping such a call), or an object with fields `text` (the reference text), `name` (the name of the
reference, as in `<nowiki><ref name="foo">...</ref></nowiki>` or `<nowiki><ref name="foo" /></nowiki>`) and/or `group`
(the group of the reference, as in `<nowiki><ref name="foo" group="bar">...</ref></nowiki>` or
`<nowiki><ref name="foo" group="bar"/></nowiki>`).
]==]
function export.format_references(refspecs)
	local refs = {}
	for _, refspec in ipairs(refspecs) do
		if type(refspec) ~= "table" then
			refspec = {text = refspec}
		end
		local refargs
		if refspec.name or refspec.group then
			refargs = {name = refspec.name, group = refspec.group}
		end
		table.insert(refs, mw.getCurrentFrame():extensionTag("ref", refspec.text, refargs))
	end
	return table.concat(refs)
end

return export