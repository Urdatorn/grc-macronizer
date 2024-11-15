local export = {}

local debug_track_module = "debug.track"
local families_module = "families"
local function_module = "fun"
local labels_module = "labels"
local languages_module = "languages"
local pages_module = "pages"
local parse_utilities_module = "Module:parse utilities"
local references_module = "Module:references"
local scripts_module = "scripts"
local string_utilities_module = "Module:string utilities"
local table_module = "table"
local wikimedia_languages_module = "Module:wikimedia languages"

local require = require
local require_when_needed = require("Module:require when needed")

local m_str_utils = require(string_utilities_module)

local dump = mw.dumpObject
local find = string.find
local floor = math.floor
local gsplit = m_str_utils.gsplit
local gsub = string.gsub
local huge = math.huge
local insert = table.insert
local ipairs = ipairs
local is_callable = require(function_module).is_callable
local is_valid_title = require_when_needed(pages_module, "is_valid_title")
local list_to_set = require_when_needed(table_module, "listToSet")
local list_to_text = mw.text.listToText
local make_title = mw.title.makeTitle
local match = string.match
local max = math.max
local new_title = mw.title.new
local pairs = pairs
local pattern_escape = m_str_utils.pattern_escape
local rawset = rawset
local remove_holes = require_when_needed("Module:parameters/remove holes")
local rsplit = m_str_utils.split
local scribunto_param_key = m_str_utils.scribunto_param_key
local sort = table.sort
local split_on_comma = require_when_needed(parse_utilities_module, "split_on_comma")
local tonumber = tonumber
local tostring = tostring
local trim = m_str_utils.trim
local type = type
local yesno = require_when_needed("Module:yesno")

local current_title -- Current title.
local current_namespace -- Current namespace.
local frame_title -- Title of the originating module.
local parent_frame_title -- Title of the page containing {{#invoke:}} (if any).
local is_invoke_page -- Whether the current title is either of those titles.
do
	local page_title_obj = mw.title.getCurrentTitle()
	current_title = page_title_obj.prefixedText
	current_namespace = page_title_obj.namespace
	
	local frame = mw.getCurrentFrame()
	frame_title = frame:getTitle()
	
	local parent_frame = frame:getParent()
	if parent_frame then
		parent_frame_title = parent_frame:getTitle()
	end
	
	is_invoke_page = current_title == frame_title or current_title == parent_frame_title
end

--[==[ intro:
This module is used to standardize template argument processing and checking. A typical workflow is as follows (based
on [[Module:translations]]):

{
	...
	local parent_args = frame:getParent().args

	local params = {
		[1] = {required = true, type = "language", default = "und"},
		[2] = true,
		[3] = {list = true},
		["alt"] = true,
		["id"] = true,
		["sc"] = {type = "script"},
		["tr"] = true,
		["ts"] = true,
		["lit"] = true,
	}

	local args = require("parameters").process(parent_args, params)

	-- Do further processing of the parsed arguments in `args`.
	...
}

The `params` table should have the parameter names as the keys, and a (possibly empty) table of parameter tags as the
value. An empty table as the value merely states that the parameter exists, but should not receive any special
treatment; if desired, empty tables can be replaced with the value `true` as a perforamnce optimization.

Possible parameter tags are listed below:

; {required = true}
: The parameter is required; an error is shown if it is not present. The template's page itself is an exception; no
  error is shown there.
; {default =}
: Specifies a default input value for the parameter, if it is absent or empty. This will be processed as though it were
  the input instead, so (for example) {default = "und"} with the type {"language"} will return a language object for
  [[:Category:Undetermined language|Undetermined language]] if no language code is provided. When used on list
  parameters, this specifies a default value for the first item in the list only. Note that it is not possible to
  generate a default that depends on the value of other parameters. If used together with {required = true}, the default
  applies only to template pages (see the following entry), as a side effect of the fact that "required" parameters
  aren't actually required on template pages. This can be used to show an example of the template in action when the
  template page is visited; however, it is preferred to use `template_default` for this purpose, for clarity.
; {template_default =}
: Specifies a default input value for absent or empty parameters only on template pages. Template pages are any page in
  the template space (beginning with `Template:`) except for documentation pages (those ending in `.../documentation`).
  This can be used to provide an example value for a non-required parameter when the template page is visited, without
  interfering with other uses of the template. Both `template_default` and `default` can be specified for the same
  parameter. If this is done, `template_default` applies on template pages, and `default` on other pages. As an example,
  {{tl|cs-IPA}} uses the equivalent of {[1] = {default = "+", template_default = "příklad"}} to supply a default of
  {"+"} for mainspace and documentation pages (which tells the module to use the value of the {{para|pagename}}
  parameter, falling back to the actual pagename), but {"příklad"} (which means "example"), on [[Template:cs-IPA]].
; {alias_of =}
: Treat the parameter as an alias of another. When arguments are specified for this parameter, they will automatically
  be renamed and stored under the alias name. This allows for parameters with multiple alternative names, while still
  treating them as if they had only one name. The conversion-related properties of an aliased parameter (e.g. `type`,
  `set`, `convert`, `sublist`) are taken from the aliasee, and the corrresponding properties set on the alias itself
  are ignored; but other properties on the alias are taken from the alias's spec and not from the aliasee's spec. This
  means, for example, that if you create an alias of a list parameter, the alias must also specify the `list` property
  or it is not a list. (In such a case, a value specified for the alias goes into the first item of the aliasee's list.
  You cannot make a list alias of a non-list parameter; this causes an error to be thrown.) Similarly, if you specify
  `separate_no_index` on an aliasee but not on the alias, uses of the unindexed aliasee parameter are stored into the
  `.default` key, but uses of the unindexed alias are stored into the first numbered key of the aliasee's list.
  Aliases cannot be required, as this prevents the other name or names of the parameter from being used. Parameters
  that are aliases and required at the same time cause an error to be thrown.
; {allow_empty = true}
: If the argument is an empty string value, it is not converted to {nil}, but kept as-is. The use of `allow_empty` is
  disallowed if a type has been specified, and causes an error to be thrown.
; {no_trim = true}
: Spacing characters such as spaces and newlines at the beginning and end of a positional parameter are not removed.
  (MediaWiki itself automatically trims spaces and newlines at the edge of named parameters.) The use of `no_trim` is
  disallowed if a type has been specified, and causes an error to be thrown.
; {type =}
: Specifies what value type to convert the argument into. The default is to leave it as a text string. Alternatives are:
:; {type = "boolean"}
:: The value is treated as a boolean value, either true or false. No value, the empty string, and the strings {"0"},
   {"no"}, {"n"} and {"false"} are treated as {false}, all other values are considered {true}.
:; {type = "number"}
:: The value is converted into a number, and throws an error if the value is not parsable as a number. Input values may
   be signed (`+` or `-`), and may contain decimal points and leading zeroes. If {allow_hex = true}, then hexadecimal
   values in the form {"0x100"} may optionally be used instead, which otherwise have the same syntax restrictions
   (including signs, decimal digits, and leading zeroes after {"0x"}). Hexadecimal inputs are not case-sensitive. Lua's
   special number values (`inf` and `nan`) are not possible inputs.
:; {type = "language"}
:: The value is interpreted as a full or [[Wiktionary:Languages#Etymology-only languages|etymology-only language]] code
   language code (or name, if {method = "name"}) and converted into the corresponding object (see [[Module:languages]]).
   If the code or name is invalid, then an error is thrown. The additional setting {family = true} can be given to allow
   [[Wiktionary:Language families|language family codes]] to be considered valid and the corresponding object returned.
   Note that to distinguish an etymology-only language object from a full language object, use
   {object:hasType("language", "etymology-only")}.
:; {type = "full language"}
:: The value is interpreted as a full language code (or name, if {method = "name"}) and converted into the corresponding
   object (see [[Module:languages]]). If the code or name is invalid, then an error is thrown. Etymology-only languages
   are not allowed. The additional setting {family = true} can be given to allow
   [[Wiktionary:Language families|language family codes]] to be considered valid and the corresponding object returned.
:; {type = "wikimedia language"}
:: The value is interpreted as a code and converted into a wikimedia language object. If the code is invalid, then an
   error is thrown. If {method = "fallback"} is specified, conventional language codes which are different from their
   Wikimedia equivalent will also be accepted as a fallback.
:; {type = "family"}
:: The value is interpreted as a language family code (or name, if {method = "name"}) and converted into the
   corresponding object (see [[Module:families]]). If the code or name is invalid, then an error is thrown.
:; {type = "script"}
:: The value is interpreted as a script code (or name, if {method = "name"}) and converted into the corresponding object
   (see [[Module:scripts]]). If the code or name is invalid, then an error is thrown.
:; {type = "title"}
:: The value is interpreted as a page title and converted into the corresponding object (see the [[mw:Extension:Scribunto/Lua_reference_manual#Title_library|Title library]]). If the page title is invalid, then an error is thrown. If {namespace = n} (where {n} is a namespace number), then the title object will be in that namespace unless overridden by a namespace prefix in the value; this is the way that template invocations work, where the template namespace is used by default, but can be overridden. If {strict = true}, then the namespace prefix is unconditionally added to the value in all cases, even if a prefix is already present; this is way that {{tl|#invoke:}} works, where the "Module:" prefix is always appended no matter what.
:; {type = "qualifier"}
:: The value is interpreted as a qualifier and converted into the correct format for passing into `format_qualifiers()`
   in [[Module:qualifier]] (which currently just means converting it to a one-item list).
:; {type = "labels"}
:: The value is interpreted as a comma-separated list of labels and converted into the correct format for passing into
   `show_labels()` in [[Module:labels]] (which is currently a list of strings). Splitting is done on commas not followed
   by whitespace, except that commas inside of double angle brackets do not count even if not followed by whitespace.
   This type should be used by for normal labels (typically specified using {{para|l}} or {{para|ll}}) and accent
   qualifiers (typically specified using {{para|a}} and {{para|aa}}).
:; {type = "references"}
:: The value is interpreted as one or more references, in the format prescribed by `parse_references()` in
   [[Module:references]], and converted into a list of objects of the form accepted by `format_references()` in the same
   module. If a syntax error is found in the reference format, an error is thrown.
:; {type = function(val) ... end}
:: `type` may be set to a function (or callable table), which must take the argument value as its sole argument, and must
   output one of the other recognized types. This is particularly useful for lists (see below), where certain values need
   to be interpreted differently to others.
; {list =}
: Treat the parameter as a list of values, each having its own parameter name, rather than a single value. The
  parameters will have a number at the end, except optionally for the first (but see also {require_index = true}). For
  example, {list = true} on a parameter named "head" will include the parameters {{para|head}} (or {{para|head1}}),
  {{para|head2}}, {{para|head3}} and so on. If the parameter name is a number, another number doesn't get appended, but
  the counting simply continues, e.g. for parameter {3} the sequence is {{para|3}}, {{para|4}}, {{para|5}} etc. List
  parameters are returned as numbered lists, so for a template that is given the parameters `|head=a|head2=b|head3=c`,
  the processed value of the parameter {"head"} will be { { "a", "b", "c" }}}.
: The value for {list =} can also be a string. This tells the module that parameters other than the first should have a
  different name, which is useful when the first parameter in a list is a number, but the remainder is named. An example
  would be for genders: {list = "g"} on a parameter named {1} would have parameters {{para|1}}, {{para|g2}}, {{para|g3}}
  etc.
: If the number is not located at the end, it can be specified by putting {"\1"} at the number position. For example,
  parameters {{para|f1accel}}, {{para|f2accel}}, ... can be captured by using the parameter name {"f\1accel"}, as is
  done in [[Module:headword/templates]].
; {set =}
: Require that the value of the parameter be one of the specified list of values (or omitted, if {required = true} isn't
  given). The values in the specified list should be strings corresponding to the raw parameter values except when
  {type = "number"}, in which case they should be numbers. The use of `set` is disallowed if {type = "boolean"} and
  causes an error to be thrown.
; {sublist =}
: The value of the parameter is a delimiter-separated list of individual raw values. The resulting field in `args` will
  be a Lua list (i.e. a table with numeric indices) of the converted values. If {sublist = true} is given, the values
  will be split on commas (possibly with whitespace on one or both sides of the comma, which is ignored). If
  {sublist = "comma without whitespace"} is given, the values will be split on commas which are not followed by whitespace,
  and which aren't preceded by an escaping backslash. Otherwise, the value of `sublist` should be either a Lua pattern
  specifying the delimiter(s) to split on or a function (or callable table) to do the splitting, which is passed two values
  (the value to split and a function to signal an error) and should return a list of the split values.
; {convert =}
: If given, this specifies a function (or callable table) to convert the raw parameter value into the Lua object used
  during further processing. The function is passed two arguments, the raw parameter value itself and a function used to
  signal an error during parsing or conversion, and should return one value, the converted parameter. The error-signaling
  function contains the name and raw value of the parameter embedded into the message it generates, so these do not need to
  specified in the message passed into it. If `type` is specified in conjunction with `convert`, the processing by
  `type` happens first. If `sublist` is given in conjunction with `convert`, the raw parameter value will be split
  appropriately and `convert` called on each resulting item.
; {allow_hex = true}
: When used in conjunction with {type = "number"}, allows hexadecimal numbers as inputs, in the format {"0x100"} (which is
  not case-sensitive).
; {family = true}
: When used in conjunction with {type = "language"}, allows [[Wiktionary:Language families|language family codes]] to be
  returned. To check if a given object refers to a language family, use {object:hasType("family")}.
; {method = "name"}
: When used in conjunction with {type = "language"}, {type = "family"} or {type = "script"}, checks for and parses a
  language, family or script name instead of a code.
; {allow_holes = true}
: This is used in conjunction with list-type parameters. By default, the values are tightly packed in the resulting
  list. This means that if, for example, an entry specified `head=a|head3=c` but not {{para|head2}}, the returned list
  will be { {"a", "c"}}}, with the values stored at the indices {1} and {2}, not {1} and {3}. If it is desirable to keep
  the numbering intact, for example if the numbers of several list parameters correlate with each other (like those of
  {{tl|affix}}), then this tag should be specified.
: If {allow_holes = true} is given, there may be {nil} values in between two real values, which makes many of Lua's
  table processing functions no longer work, like {#} or {ipairs()}. To remedy this, the resulting table will contain an
  additional named value, `maxindex`, which tells you the highest numeric index that is present in the table. In the
  example above, the resulting table will now be { { "a", nil, "c", maxindex = 3}}}. That way, you can iterate over the
  values from {1} to `maxindex`, while skipping {nil} values in between.
; {disallow_holes = true}
: This is used in conjunction with list-type parameters. As mentioned above, normally if there is a hole in the source
  arguments, e.g. `head=a|head3=c` but not {{para|head2}}, it will be removed in the returned list. If
  {disallow_holes = true} is specified, however, an error is thrown in such a case. This should be used whenever there
  are multiple list-type parameters that need to line up (e.g. both {{para|head}} and {{para|tr}} are available and
  {{para|head3}} lines up with {{para|tr3}}), unless {allow_holes = true} is given and you are prepared to handle the
  holes in the returned lists.
; {require_index = true}
: This is used in conjunction with list-type parameters. By default, the first parameter can have its index omitted.
  For example, a list parameter named `head` can have its first parameter specified as either {{para|head}} or
  {{para|head1}}. If {require_index = true} is specified, however, only {{para|head1}} is recognized, and {{para|head}}
  will be treated as an unknown parameter. {{tl|affixusex}} (and variants {{tl|suffixusex}}, {{tl|prefixusex}}) use
  this, for example, on all list parameters.
; {separate_no_index = true}
: This is used to distinguish between {{para|head}} and {{para|head1}} as different parameters. For example, in
  {{tl|affixusex}}, to distinguish between {{para|sc}} (a script code for all elements in the usex's language) and
  {{para|sc1}} (the script code of the first element, used when the first element is prefixed with a language code to
  indicate that it is in a different language). When this is used, the resulting table will contain an additional named
  value, `default`, which contains the value for the indexless argument.
; {demo = true}
: This is used as a way to ensure that the parameter is only enabled on the template's own page (and its documentation page), and in the User: namespace; otherwise, it will be treated as an unknown parameter. This should only be used if special settings are required to showcase a template in its documentation (e.g. adjusting the pagename or disabling categorization). In most cases, it should be possible to do this without using demo parameters, but they may be required if a template/documentation page also contains real uses of the same template as well (e.g. {{tl|shortcut}}), as a way to distinguish them.
]==]

local function track(page)
	local tracking_page = "parameters/" .. page
	local pages, current, mod, func = {tracking_page}
	-- Check through the traceback to get the calling module and function.
	for mod, func in debug.traceback():gmatch("%f[^%z\n]\tModule:(.-):%d+: in function '(.-)'%f[%z\n]") do
		if current == nil then
			current = mod -- Name of this module.
		elseif mod ~= current then
			insert(pages, tracking_page .. "/" .. mod)
			-- FIXME: if the calling function is the one called by #invoke:, traceback calls it "chunk" instead of its actual name.
			insert(pages, tracking_page .. "/" .. mod .. "/" .. func)
			break
		end
	end
	require(debug_track_module)(pages)
end

-------------------------------------- Some splitting functions -----------------------------

-- Split an argument on comma, but not comma followed by whitespace.
local function split_on_comma_without_whitespace(val)
	if find(val, "\\", 1, true) or match(val, ",%s") then
		return split_on_comma(val)
	else
		return rsplit(val, ",")
	end
end

-------------------------------------- Error handling -----------------------------

local function process_error(fmt, ...)
	local args = {...}
	for i, val in ipairs(args) do
		args[i] = dump(val)
	end
	if type(fmt) == "table" then
		-- hacky signal that we're called from internal_process_error(), and not to omit stack frames
		return error(fmt[1]:format(unpack(args)))
	else
		return error(fmt:format(unpack(args)), 3)
	end
end

local function internal_process_error(fmt, ...)
	fmt = "Internal error in `params` table: " .. fmt
	process_error({fmt}, ...)
end

-------------------------------------- Value conversion -----------------------------

-- For a list parameter `name` and corresponding value `list_name` of the `list` field (which should have the same value
-- as `name` if `list = true` was given), generate a pattern to match parameters of the list and store the pattern as a
-- key in `patterns`, with corresponding value set to `name`. For example, if `list_name` is "tr", the pattern will
-- match "tr" as well as "tr1", "tr2", ..., "tr10", "tr11", etc. If the `list_name` contains a \1 in it, the numeric
-- portion goes in place of the \1. For example, if `list_name` is "f\1accel", the pattern will match "faccel",
-- "f1accel", "f2accel", etc. Any \1 in `name` is removed before storing into `patterns`.
local function save_pattern(name, list_name, patterns)
	name = type(name) == "string" and gsub(name, "\1", "") or name
	if match(list_name, "\1") then
		patterns["^" .. gsub(pattern_escape(list_name), "\1", "([1-9]%%d*)") .. "$"] = name
	else
		patterns["^" .. pattern_escape(list_name) .. "([1-9]%d*)$"] = name
	end
end

-- Convert a list in `list` to a string, separating the final element from the preceding one(s) by `conjunction`. If
-- `dump_vals` is given, pass all values in `list` through mw.dumpObject() (WARNING: this destructively modifies
-- `list`). This is similar to serialCommaJoin() in [[Module:table]] when used with the `dontTag = true` option, but
-- internally uses mw.text.listToText().
local function concat_list(list, conjunction, dump_vals)
	if dump_vals then
		for i = 1, #list do
			list[i] = dump(list[i])
		end
	end
	return list_to_text(list, nil, conjunction)
end

-- Helper function for use with convert_val_error(). Format a list of possible choices using `concat_list` and
-- conjunction "or", displaying "either " before the choices if there's more than one.
local function format_choice_list(typ)
	return (#typ > 1 and "either " or "") .. concat_list(typ, " or ")
end

-- Signal an error for a value `val` that is not of the right typ `typ` (which is either a string specifying a type or
-- a list of possible values, in the case where `set` was used). `name` is the name of the parameter and can be a
-- function to signal an error (which is assumed to automatically display the parameter's name and value). `seetext` is
-- an optional additional explanatory link to display (e.g. [[WT:LOL]], the list of possible languages and codes).
local function convert_val_error(val, name, typ, seetext)
	if is_callable(name) then
		if type(typ) == "table" then
			typ = "choice, must be " .. format_choice_list(typ)
		end
		name(("Invalid %s; the value %s is not valid%s"):format(typ, val, seetext and "; see " .. seetext or ""))
	else
		if type(typ) == "table" then
			typ = "must be " .. format_choice_list(typ)
		else
			typ = "should be a valid " .. typ
		end
		error(("Parameter %s %s; the value %s is not valid.%s"):format(dump(name), typ, dump(val),
			seetext and " See " .. seetext .. "." or ""))
	end
end

-- Convert a value that is not a string or number to a string using mw.dumpObject(), for debugging purposes.
local function dump_if_unusual(val)
	local val_type = type(val)
	return (val_type == "string" or val_type == "number") and val or dump(val)
end

-- A helper function for use with generating error-signaling functions in the presence of raw value conversion. Format a
-- message `msg`, including the processed value `processed` if it is different from the raw value `rawval`; otherwise,
-- just return `msg`.
local function msg_with_processed(msg, rawval, processed)
	if rawval == processed then
		return msg
	else
		return ("%s (processed value %s)"):format(msg, dump_if_unusual(processed))
	end
end

-- Generate the appropriate error-signaling function given parameter value `val` and name `name`. If `name` is already
-- a function, it is just returned; otherwise a function is generated and returned that displays the passed-in messaeg
-- along with the parameter's name and value.
local function make_parse_err(val, name)
	if is_callable(name) then
		return name
	else
		return function(msg)
			error(("%s: parameter %s=%s"):format(msg, name, val))
		end
	end
end

-- A reimplementation of ipairs() for use in a single-variable for-loop (like with gsplit()) instead of a two-variable
-- for-loop (like with ipairs()). If we changed the return statement below to `return index, list[index]`, we'd get
-- ipairs() directly.
local function iterate_over_list(list)
   local index, len = 0, #list
   return function()
      index = index + 1
      if index <= len then
         return list[index]
      end
   end
end

-- A helper function for use with `sublist`. It is an iterator function for use in a for-loop that returns split
-- elements of `val` using `sublist` (a Lua split pattern; boolean `true` to split on commas optionally surrounded by
-- whitespace; "comma without whitespace" to split only on commas not followed by whitespace which have not been escaped
-- by a backslash; or a function to do the splitting, which is passed two values, the value to split and a function to
-- signal an error, and should return a list of the split elements). `name` is the parameter name or error-signaling
-- function passed into convert_val().
local function split_sublist(val, name, sublist)
	if sublist == true then
		sublist = "%s*,%s*"
	elseif sublist == "comma without whitespace" then
		sublist = split_on_comma_without_whitespace
	end
	if type(sublist) == "string" then
		return gsplit(val, sublist)
	elseif is_callable(sublist) then
		local retval = sublist(val, make_parse_err(val, name))
		return iterate_over_list(retval)
	else
		error(('Internal error: Expected `sublist` to be of type "string" or "function" or boolean `true`, but saw %s'):format(dump(sublist)))
	end
end

-- For parameter named `name` with value `val` and param spec `param`, if the `set` field is specified, verify that the
-- value is one of the one specified in `set`, and throw an error otherwise. `name` is taken directly from the
-- corresponding parameter passed into convert_val() and may be a function to signal an error. Optional `typ` is a
-- string specifying the conversion type of `val` and is used for special-casing: If `typ` is "boolean", an internal
-- error is thrown (since `set` cannot be used in conjunction with booleans) and if `typ` is "number", no checking
-- happens because in this case `set` contains numbers and is checked inside the number conversion function itself,
-- after converting `val` to a number.
local function check_set(val, name, param, typ)
	if typ == "boolean" then
		error(('Internal error: Cannot use `set` with `type = "%s"`'):format(typ))
	end
	if typ == "number" then
		-- Needs to be special cased because the check happens after conversion to numbers.
		return
	end
	if not param.set[val] then
		local list = {}
		for k in pairs(param.set) do
			insert(list, dump(k))
		end
		sort(list)
		-- If the parameter is not required then put "or empty" at the end of the list, to avoid implying the parameter is actually required.
		if not param.required then
			insert(list, "empty")
		end
		convert_val_error(val, name, list)
	end
end

local function convert_language(val, name, param, allow_etym)
	local lang = require(languages_module)[param.method == "name" and "getByCanonicalName" or "getByCode"](val, nil, allow_etym, param.family)
	if lang then
		return lang
	end
	local list = {"language"}
	local links = {"[[WT:LOL]]"}
	if allow_etym then
		insert(list, "etymology language")
		insert(links, "[[WT:LOL/E]]")
	end
	if param.family then
		insert(list, "family")
		insert(links, "[[WT:LOF]]")
	end
	convert_val_error(val, name, concat_list(list, " or ") .. " " .. (param.method == "name" and "name" or "code"),
		concat_list(links, " and "))
end
	
--[==[ func: export.convert_val(val, name, param)
Convert a parameter value according to the associated specs listed in the `params` table passed to
[[Module:parameters]]. `val` is the value to convert for a parameter whose name is `name` (used only in error messages).
`param` is the spec (the value part of the `params` table for the parameter). In place of passing in the parameter name,
`name` can be a function that throws an error, displaying the specified message along with the parameter name and value.
This function processes all the conversion-related fields in `param`, including `type`, `set`, `sublist`, `convert`,
etc. It returns the converted value.
]==]
local convert_val = setmetatable({
	["boolean"] = function(val)
		return yesno(val, true)
	end,
	
	["family"] = function(val, name, param)
		return require(families_module)[param.method == "name" and "getByCanonicalName" or "getByCode"](val) or
			convert_val_error(val, name, "family " .. (param.method == "name" and "name" or "code"), "[[WT:LOF]]")
	end,
	
	["labels"] = function(val, name, param)
		-- FIXME: Should be able to pass in a parse_err function.
		return require(labels_module).split_labels_on_comma(val)
	end,

	["references"] = function(val, name, param)
		return require(references_module).parse_references(val, make_parse_err(val, name))
	end,

	["qualifier"] = function(val, name, param)
		return {val}
	end,

	["language"] = function(val, name, param)
		return convert_language(val, name, param, true)
	end,
	
	["full language"] = function(val, name, param)
		return convert_language(val, name, param)
	end,
	
	["number"] = function(val, name, param)
		if type(val) == "number" then
			return val
		end
		-- Avoid converting inputs like "nan" or "inf", and disallow 0x hex inputs unless explicitly enabled
		-- with `allow_hex`.
		val = tonumber(
			match(val, "^[+-]?%d+%.?%d*$") or
			param.allow_hex and match(val, "^[+-]?0[Xx]%x+%.?%x*$")
		) or convert_val_error(val, name, "number")
		if param.set then
			-- Don't pass in "number" here; otherwise no checking will happen.
			check_set(val, name, param)
		end
		return val
	end,
	
	["script"] = function(val, name, param)
		return require(scripts_module)[param.method == "name" and "getByCanonicalName" or "getByCode"](val) or
			convert_val_error(val, name, "script " .. (param.method == "name" and "name" or "code"), "[[WT:LOS]]")
	end,
	
	["string"] = function(val, name, param)
		return val
	end,
	
	["title"] = function(val, name, param)
		val = tostring(val)
		local namespace, title = param.namespace
		if param.strict then
			-- Always applies the namespace prefix.
			title = make_title(namespace or 0, val)
		else
			-- Applies the namespace prefix if `val` doesn't contain one already.
			title = new_title(val, namespace)
			-- If the input starts with an interwiki prefix, the returned title will be an interwiki title. If `namespace` is specified and not the mainspace, force the title to be a namespace title instead (e.g. "el:All topics" with namespace = 14 returns "el:Category:All topics", but we want "Category:el:All topics" instead).
			if title and title.isExternal and namespace and namespace ~= 0 then
				title = make_title(namespace, val)
			end
		end
		return is_valid_title(title) and title or convert_val_error(val, name, "Wiktionary page title")
	end,
	
	["wikimedia language"] = function(val, name, param)
		local fallback = param.method == "fallback"
		local lang = require(wikimedia_languages_module)[fallback and "getByCodeWithFallback" or "getByCode"](val)
		if lang then
			return lang
		end
		local list = {"wikimedia language"}
		if fallback then
			insert(list, "language")
		end
		convert_val_error(val, name, concat_list(list, " or ") .. " code")
	end,
}, {
	__call = function(self, val, name, param)
		local typ = param.type or "string"
		-- If param.type is a function, resolve it to a recognized type.
		if is_callable(typ) then
			typ = typ(val)
		end
		local func, sublist = self[typ], param.sublist
		if not func then
			error("Internal error: " .. dump(typ) .. " is not a recognized parameter type.")
		elseif sublist then
			local retlist = {}
			if type(val) ~= "string" then
				error("Internal error: " .. dump(val) .. " is not a string.")
			end
			if param.convert then
				local thisval, insval
				local thisindex = 0
				local parse_err
				if is_callable(name) then
					-- We assume the passed-in error function in `name` already shows the parameter name and raw value.
					parse_err = function(msg)
						name(("%s: item #%s=%s"):format(msg_with_processed(msg, thisval, insval), thisindex,
							thisval))
					end
				else
					parse_err = function(msg)
						error(("%s: item #%s=%s of parameter %s=%s"):format(msg_with_processed(msg, thisval, insval),
							thisindex, thisval, name, val))
					end
				end
				for v in split_sublist(val, name, sublist) do
					thisval = v
					thisindex = thisindex + 1
					if param.set then
						check_set(v, name, param, typ)
					end
					insval = func(v, name, param)
					insert(retlist, param.convert(insval, parse_err))
				end
			else
				for v in split_sublist(val, name, sublist) do
					if param.set then
						check_set(v, name, param, typ)
					end
					insert(retlist, func(v, name, param))
				end
			end
			return retlist
		else
			if param.set then
				check_set(val, name, param, typ)
			end
			local retval = func(val, name, param)
			if param.convert then
				local parse_err
				if is_callable(name) then
					-- We assume the passed-in error function in `name` already shows the parameter name and raw value.
					if retval == val then
						-- This is an optimization to avoid creating a closure. The second arm works correctly even
						-- when retval == val.
						parse_err = name
					else
						parse_err = function(msg)
							name(msg_with_processed(msg, val, retval))
						end
					end
				else
					parse_err = function(msg)
						error(("%s: parameter %s=%s"):format(msg_with_processed(msg, val, retval), name, val))
					end
				end
				retval = param.convert(retval, parse_err)
			end
			return retval
		end
	end
})
export.convert_val = convert_val -- used by [[Module:parameter utilities]]

local function unknown_param(name, val, args_unknown, return_unknown)
	if not return_unknown then
		process_error("Parameter %s is not used by this template.", name)
	end
	args_unknown[name] = val
	track("unknown")
end

local function check_demo_param()
	if current_namespace == 2 or is_invoke_page then
		return true
	elseif current_namespace ~= 10 and current_namespace ~= 828 then -- Template: and Module:
		return false
	elseif ( -- Template or module documentation page.
		current_title == frame_title .. "/documentation" or
		parent_frame_title and current_title == parent_frame_title .. "/documentation"
	) then
		return true
	end
	return false
end

local function check_string_param(typ, name, tag)
	if typ and typ ~= "string" then
		internal_process_error(
			"%s cannot be set unless the parameter has the type %s (the default): parameter %s has the type %s.",
			tag, "string", name, typ)
	end
end

--[==[
Process arguments with a given list of parameters. Return a table containing the processed arguments. The `args`
parameter specifies the arguments to be processed; they are the arguments you might retrieve from
{frame:getParent().args} (the template arguments) or in some cases {frame.args} (the invocation arguments). The `params`
parameter specifies a list of valid parameters, and consists of a table. If an argument is encountered that is not in
the parameter table, an error is thrown.

The structure of the `params` table is as described above in the intro comment.

'''WARNING:''' The `params` table is destructively modified to save memory. Nonetheless, different keys can share the
same value objects in memory without causing problems.

The `return_unknown` parameter, if set to {true}, prevents the function from triggering an error when it comes across an
argument with a name that it doesn't recognise. Instead, the return value is a pair of values: the first is the
processed arguments as usual, while the second contains all the unrecognised arguments that were left unprocessed. This
allows you to do multi-stage processing, where the entire set of arguments that a template should accept is not known at
once. For example, an inflection-table might do some generic processing on some arguments, but then defer processing of
the remainder to the function that handles a specific inflectional type.
]==]
function export.process(args, params, return_unknown)
	-- Process parameters for specific properties
	local args_new = {}
	local param_types = {}
	local required = {}
	local patterns = {}
	local has_placeholder = {}
	local list_from_index
	
	for name, param in pairs(params) do
		local param_type = type(param)
		param_types[param] = param_type
		if param_type == "table" then
			-- Populate required table, and make sure aliases aren't set to required.
			if param.required then
				if param.alias_of then
					internal_process_error(
						"Parameter %s is an alias of %s, but is also set as a required parameter. Only %s should be set as required.",
						name, param.alias_of, name)
				end
				required[name] = true
			end
			
			-- Convert param.set from a list into a set.
			-- `converted_set` prevents double-conversion if multiple parameter keys share the same param table.
			-- rawset avoids errors if param has been loaded via mw.loadData; however, it's probably more efficient to preconvert them, and set the `converted_set` key in advance.
			local set = param.set
			if set and not param.converted_set then
				rawset(param, "set", list_to_set(set))
				rawset(param, "converted_set", true)
			end
			
			local alias = param.alias_of
			if alias then
				-- Check that the alias_of is set to a valid parameter.
				if not params[alias] then
					internal_process_error("Parameter %s is an alias of an invalid parameter.", name)
				end
				-- Check that all the parameters in params are in the form Scribunto normalizes input argument keys into (e.g. 1 not "1", "foo" not " foo "). Otherwise, this function won't be able to normalize the input arguments in the expected way.
				local normalized = scribunto_param_key(alias)
				if alias ~= normalized then
					internal_process_error(
						"Parameter %s (a " .. type(alias) .. ") given in the alias_of field of parameter %s is not a normalized Scribunto parameter. Should be %s (a " .. type(normalized) .. ").",
						alias, name, normalized)
				end
				local main_param = params[alias]
				local main_type = type(main_param) -- Might not yet be memoized.
				-- Aliases can't be lists unless the canonical parameter is also a list.
				if param.list and not (main_type == "table" and main_param.list) then
					internal_process_error(
						"The list parameter %s is set as an alias of %s, which is not a list parameter.", name, alias)
				-- Aliases can't be aliases of other aliases.
				elseif main_type == "table" and main_param.alias_of then
					internal_process_error(
						"alias_of cannot be set to another alias: parameter %s is set as an alias of %s, which is in turn an alias of %s. Set alias_of for %s to %s.",
						name, alias, params[alias].alias_of, name, params[alias].alias_of)
				end
			end
			
			local normalized = scribunto_param_key(name)
			if name ~= normalized then
				internal_process_error(
					"Parameter %s (a " .. type(name) .. ") is not a normalized Scribunto parameter. Should be %s (a " ..
					type(normalized) .. ").",
					name, normalized)
			end
			
			if param.list then
				if not param.alias_of then
					local key = name
					if type(name) == "string" then
						key = gsub(name, "\1", "")
					end
					-- _list is used as a temporary flag.
					args_new[key] = {maxindex = 0, _list = param.list}
				end
				
				if type(param.list) == "string" then
					-- If the list property is a string, then it represents the name
					-- to be used as the prefix for list items. This is for use with lists
					-- where the first item is a numbered parameter and the
					-- subsequent ones are named, such as 1, pl2, pl3.
					save_pattern(name, param.list, patterns)
				elseif type(name) == "number" then
					if list_from_index then
						internal_process_error(
							"Only one numeric parameter can be a list, unless the list property is a string.")
					end
					-- If the name is a number, then all indexed parameters from
					-- this number onwards go in the list.
					list_from_index = name
				else
					save_pattern(name, name, patterns)
				end
				
				if match(name, "\1") then
					insert(has_placeholder, name)
				end
			end
		elseif param ~= true then
			internal_process_error("Spec for parameter %s must be a table of specs or the value true, but found %s.", name, param_type ~= "boolean" and param_type or param)
		end
	end
	
	--Process required changes to `params`.
	for i = 1, #has_placeholder do
		local name = has_placeholder[i]
		params[gsub(name, "\1", "")] = params[name]
		params[name] = nil
	end
	
	-- Process the arguments
	local args_unknown = {}
	
	for name, val in pairs(args) do
		local orig_name, raw_type, index, normalized = name, type(name)
		
		if raw_type == "number" then
			if list_from_index ~= nil and name >= list_from_index then
				index = name - list_from_index + 1
				name = list_from_index
			end
		else
			-- Does this argument name match a pattern?
			for pattern, pname in pairs(patterns) do
				index = match(name, pattern)
				-- It matches, so store the parameter name and the
				-- numeric index extracted from the argument name.
				if index then
					index = tonumber(index)
					name = pname
					break
				end
			end
		end
		
		local param = params[name]
		
		-- If the argument is not in the list of parameters, trigger an error.
		-- return_unknown suppresses the error, and stores it in a separate list instead.
		if not param then
			unknown_param(name, val, args_unknown, return_unknown)
		elseif param == true then
			normalized = orig_name
			val = trim(val)
			if val ~= "" then
				-- If the parameter is duplicated, throw an error.
				if args_new[name] ~= nil then
					process_error(
						"Parameter %s has been entered more than once. This is probably because a parameter alias has been used.",
						normalized)
				end
				args_new[name] = val
			end
		else
			if param.require_index then
				-- Disallow require_index for numeric parameter names, as this doesn't make sense.
				if raw_type == "number" then
					internal_process_error("Cannot set require_index for numeric parameter %s.", name)
				-- If a parameter without the trailing index was found, and
				-- require_index is set on the param, treat it
				-- as if it isn't recognized.
				elseif not index then
					unknown_param(name, val, args_unknown, return_unknown)
				end
			end
			
			-- Check that separate_no_index is not being used with a numeric parameter.
			if param.separate_no_index then
				if raw_type == "number" then
					internal_process_error("Cannot set separate_no_index for numeric parameter %s.", name)
				elseif type(param.alias_of) == "number" then
					internal_process_error(
						"Cannot set separate_no_index for parameter %s, as it is an alias of numeric parameter %s.",
						name, param.alias_of)
				end
			end
			
			-- If no index was found, use 1 as the default index.
			-- This makes list parameters like g, g2, g3 put g at index 1.
			-- If `separate_no_index` is set, then use 0 as the default instead.
			if param.list then
				index = index or param.separate_no_index and 0 or 1
			end
			
			-- Normalize to the canonical parameter name. If it's a list, but the alias is not, then determine the index.
			local raw_name = param.alias_of
			if param.alias_of then
				raw_type = type(raw_name)
				if raw_type == "number" then
					local main_param = params[raw_name]
					if param_types[main_param] == "table" and main_param.list then
						index = index or param.separate_no_index and 0 or 1
						normalized = raw_name + index - 1
					else
						normalized = raw_name
					end
					name = raw_name
				else
					name = gsub(raw_name, "\1", "")
					local main_param = params[name]
					if param_types[main_param] == "table" and main_param.list then
						index = index or param.separate_no_index and 0 or 1
					end
					if not index or index == 0 then
						normalized = name
					elseif name == raw_name then
						normalized = name .. index
					else
						normalized = gsub(raw_name, "\1", index)
					end
				end
			else
				normalized = orig_name
			end
			
			-- Only allow demo parameters if the current page contains the originating
			-- {{#invoke:}}, or this is the User: namespace.
			if param.demo and not check_demo_param() then
				unknown_param(name, val, args_unknown, return_unknown)
			end
			
			-- Remove leading and trailing whitespace unless no_trim is true.
			if param.no_trim then
				check_string_param(param.type, name, "no_trim")
			else
				val = trim(val)
			end
			
			-- Empty string is equivalent to nil unless allow_empty is true.
			if param.allow_empty then
				check_string_param(param.type, name, "allow_empty")
			elseif val == "" then
				val = nil
			end
			
			-- Can't use "if val" alone, because val may be a boolean false.
			if val ~= nil then
				-- Convert to proper type if necessary.
				local main_param = params[raw_name]
				if not main_param or param_types[main_param] == "table" then
					val = convert_val(val, orig_name, main_param or param)
				end
				
				-- Mark it as no longer required, as it is present.
				required[name] = nil
				
				-- Store the argument value.
				if index then
					-- If the parameter is duplicated, throw an error.
					if args_new[name][index] ~= nil then
						process_error(
							"Parameter %s has been entered more than once. This is probably because a list parameter has been entered without an index and with index 1 at the same time, or because a parameter alias has been used.",
							normalized)
					end
					args_new[name][index] = val
					
					-- Store the highest index we find.
					args_new[name].maxindex = max(index, args_new[name].maxindex)
					if args_new[name][0] ~= nil then
						args_new[name].default = args_new[name][0]
						if args_new[name].maxindex == 0 then
							args_new[name].maxindex = 1
						end
						args_new[name][0] = nil
						
					end
					
					if params[name].list then
						-- Don't store index 0, as it's a proxy for the default.
						if index > 0 then
							args_new[name][index] = val
							-- Store the highest index we find.
							args_new[name].maxindex = max(index, args_new[name].maxindex)
						end
					else
						args_new[name] = val
					end
				else
					-- If the parameter is duplicated, throw an error.
					if args_new[name] ~= nil then
						process_error(
							"Parameter %s has been entered more than once. This is probably because a parameter alias has been used.",
							normalized)
					end
					
					if not param.alias_of then
						args_new[name] = val
					else
						local main_param = params[param.alias_of]
						if param_types[main_param] == "table" and main_param.list then
							args_new[param.alias_of][1] = val
							-- Store the highest index we find.
							args_new[param.alias_of].maxindex = max(1, args_new[param.alias_of].maxindex)
						else
							args_new[param.alias_of] = val
						end
					end
				end
			end
		end
	end
	
	-- Remove holes in any list parameters if needed.
	for name, val in pairs(args_new) do
		if type(val) == "table" then
			local listname = val._list
			if listname then
				if params[name].disallow_holes then
					local highest = 0
					for num, _ in pairs(val) do
						if type(num) == "number" and num > 0 and num < huge and floor(num) == num then
							highest = max(highest, num)
						end
					end
					for i = 1, highest do
						if val[i] == nil then
							if type(listname) == "string" then
								listname = dump(listname)
							elseif type(name) == "number" then
								i = i + name - 1 -- Absolute index.
								listname = "numeric"
							else
								listname = dump(name)
							end
							process_error(
								"Item %s in the list of " .. listname .. " parameters cannot be empty, because the list must be contiguous.",
								i)
						end
					end
					-- Some code depends on only numeric params being present
					-- when no holes are allowed (e.g. by checking for the
					-- presence of arguments using next()), so remove
					-- `maxindex`.
					val.maxindex = nil
				elseif not params[name].allow_holes then
					args_new[name] = remove_holes(val)
				end
			end
		end
	end

	-- If the current page is the template which invoked this Lua instance, then ignore the `require` flag, as it
	-- means we're viewing the template directly. Required parameters sometimes have a `template_default` key set,
	-- which gets used in such cases as a demo.
	-- Note: this won't work on other pages in the Template: namespace (including the /documentation subpage),
	-- or if the #invoke: is on a page in another namespace.
	local is_template_page = current_namespace == 10 and is_invoke_page
	local pagename_set = args_new.pagename

	-- Handle defaults.
	for name, param in pairs(params) do
		if param_types[param] == "table" then
			local default_val
			-- If both `template_default` and `default` are given, `template_default` takes precedence, but only on
			-- template pages. This lets you specify a different default as the template page example.
			-- HACK: We still run into problems on documentation pages transcluded into the template page when pagename= is
			-- set. Check this on the assumption that pagename= is fairly standard.
			if is_template_page and not pagename_set then
				default_val = param.template_default
			end
			if default_val == nil then
				default_val = param.default
			end
			if default_val ~= nil then
				local arg_new = args_new[name]
				if type(arg_new) == "table" and arg_new._list then
					if arg_new[1] == nil then
						arg_new[1] = convert_val(default_val, name, param)
					end
					if arg_new.maxindex == 0 then
						arg_new.maxindex = 1
					end
					arg_new._list = nil
				elseif arg_new == nil then
					args_new[name] = convert_val(default_val, name, param)
				end
			end
		end
	end
	
	-- The required table should now be empty.
	-- If any entry remains, trigger an error, unless we're on a template page.
	if not is_template_page then
		local list = {}
		for name in pairs(required) do
			insert(list, dump(name))
		end
		local n = #list
		if n > 0 then
			process_error("Parameter" .. (
				n == 1 and (" " .. list[1] .. " is") or
				("s " .. concat_list(list, " and ", true) .. " are")
			) .. " required.")
		end
	end
	
	-- Remove the temporary _list flag.
	for _, arg_new in pairs(args_new) do
		if type(arg_new) == "table" then
			arg_new._list = nil
		end
	end
	
	if return_unknown then
		return args_new, args_unknown
	else
		return args_new
	end
end

return export