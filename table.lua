--[[
------------------------------------------------------------------------------------
--                      table (formerly TableTools)                               --
--                                                                                --
-- This module includes a number of functions for dealing with Lua tables.        --
-- It is a meta-module, meant to be called from other Lua modules, and should     --
-- not be called directly from #invoke.                                           --
------------------------------------------------------------------------------------
--]]

--[[
	Inserting new values into a table using a local "index" variable, which is
	incremented each time, is faster than using "table.insert(t, x)" or
	"t[#t + 1] = x". See the talk page.
]]

local export = {}

local collation_module = "Module:collation"
local function_module = "Module:fun"

local require = require

local table = table

local concat = table.concat
local format = string.format
local getmetatable = getmetatable
local insert = table.insert
local ipairs = ipairs
local is_positive_integer -- defined as export.isPositiveInteger below
local keys_to_list -- defined as export.keysToList below
local length -- defined as export.length below
local next = next
local pairs = pairs
local rawequal = rawequal
local rawget = rawget
local select = select
local setmetatable = setmetatable
local sort = table.sort
local type = type
local unpack = unpack

local infinity = math.huge

-- Functions in other modules that load locally on demand by dereferencing themselves.
local function is_callable(...)
	is_callable = require(function_module).is_callable
	return is_callable(...)
end

local function string_sort(...)
	string_sort = require(collation_module).string_sort
	return string_sort(...)
end

--[==[
Return true if the given value is a positive integer, and false if not. Although it doesn't operate on tables, it is
included here as it is useful for determining whether a given table key is in the array part or the hash part of a
table.
]==]
function export.isPositiveInteger(v)
	return type(v) == "number" and v >= 1 and v % 1 == 0 and v < infinity
end
is_positive_integer = export.isPositiveInteger

--[==[
Return a clone of an object. If the object is a table, the value returned is a new table, but all subtables and functions are shared. Metamethods are respected, but the returned table will have no metatable of its own.
]==]
function export.shallowcopy(orig)
	if type(orig) ~= "table" then
		return orig
	end
	local copy = {}
	for k, v in pairs(orig) do
		copy[k] = v
	end
	return copy
end

do
	local function rawpairs(t)
		return next, t
	end

	local function make_copy(orig, memo, mt_flag, keep_loaded_data)
		if type(orig) ~= "table" then
			return orig
		end
		local memoized = memo[orig]
		if memoized ~= nil then
			return memoized
		end
		local mt = getmetatable(orig)
		local loaded_data = mt and mt.mw_loadData
		if loaded_data and keep_loaded_data then
			memo[orig] = orig
			return orig
		end
		local copy = {}
		memo[orig] = copy
		for k, v in (loaded_data and pairs or rawpairs)(orig) do
			copy[make_copy(k, memo, mt_flag, keep_loaded_data)] = make_copy(v, memo, mt_flag, keep_loaded_data)
		end
		if loaded_data then
			return copy
		elseif mt_flag == "keep" then
			setmetatable(copy, mt)
		elseif mt_flag ~= "none" then
			setmetatable(copy, make_copy(mt, memo, mt_flag, keep_loaded_data))
		end
		return copy
	end

	--[==[
	Recursive deep copy function. Preserves copied identities of subtables.
	A more powerful version of {mw.clone}, with customizable options.
	* By default, metatables are copied, except for data loaded via mw.loadData (see below). If `metatableFlag` is set to "none", the copy will not have any metatables at all. Conversely, if `metatableFlag` is set to "keep", then the cloned table (and all its members) will have the exact same metatable as their original version.
	* If `keepLoadedData` is true, then any data loaded via {mw.loadData} will not be copied, and the original will be used instead. This is useful in iterative contexts where it is necessary to copy data being destructively modified, because objects loaded via mw.loadData are immutable.
	* Notes:
	*# Protected metatables will not be copied (i.e. those hidden behind a __metatable metamethod), as they are not
	   accessible by Lua's design. Instead, the output of the __metatable method will be used instead.
	*# When iterating over the table, the __pairs metamethod is ignored, since this can prevent the table from being properly cloned.
	*# Data loaded via mw.loadData is a special case in two ways: the metatable is stripped, because otherwise the cloned table throws errors when accessed; in addition, the __pairs metamethod is used, since otherwise the cloned table would be empty.]==]
	function export.deepcopy(orig, metatableFlag, keepLoadedData)
		return make_copy(orig, {}, metatableFlag, keepLoadedData)
	end
end

--[==[
Append any number of tables together and returns the result. Compare the Lisp expression {(append list1 list2 ...)}.
]==]
function export.append(...)
	local ret, n = {}, 0
	for i = 1, arg.n do
		for _, v in ipairs(arg[i]) do
			n = n + 1
			ret[n] = v
		end
	end
	return ret
end

--[==[
Extend an existing list by a new list, modifying the existing list in-place. Compare the Python expression
{list.extend(new_items)}.

`options` is an optional table of additional options to control the behavior of the operation. The following options are
recognized:
* `insertIfNot`: Use {export.insertIfNot()} instead of {table.insert()}, which ensures that duplicate items do not get
  inserted (at the cost of an O((M+N)*N) operation, where M = #list and N = #new_items).
* `key`: As in {insertIfNot()}. Ignored otherwise.
* `pos`: As in {insertIfNot()}. Ignored otherwise.
]==]
function export.extendList(list, new_items, options)
	for _, item in ipairs(new_items) do
		if options and options.insertIfNot then
			export.insertIfNot(list, item, options)
		else
			insert(list, item)
		end
	end
end

--[==[
Remove duplicate values from an array. Non-positive-integer keys are ignored. The earliest value is kept, and all subsequent duplicate values are removed, but otherwise the array order is unchanged.
-- -0, NaN and -NaN have special handling, as they can't be used as table keys.
]==]
function export.removeDuplicates(t)
	local ret, n, seen, _neg_0, _pos_nan, _neg_nan = {}, 0, {}
	for _, v in ipairs(t) do
		local v_key = v
		-- -0
		if v == 0 and 1 / v < 0 then
			_neg_0 = _neg_0 or {}
			v_key = _neg_0
		-- NaN and -NaN.
		elseif v ~= v then
			if format("%f", v) == "nan" then
				_pos_nan = _pos_nan or {}
				v_key = _pos_nan
			else
				_neg_nan = _neg_nan or {}
				v_key = _neg_nan
			end
		end
		if not seen[v_key] then
			n = n + 1
			ret[n] = v
			seen[v_key] = true
		end
	end
	return ret
end

--[==[
Given a table, return an array containing the numbers of any positive integer keys with values, sorted in numerical order.]==]
function export.numKeys(t)
	local nums, i = {}, 0
	for k in pairs(t) do
		if is_positive_integer(k) then
			i = i + 1
			nums[i] = k
		end
	end
	sort(nums)
	return nums
end

--[==[
Return the highest positive integer index of a table or array that possibly has holes in it, or otherwise 0 if no positive integer keys are found. Note that this differs from `table.maxn`, which returns the highest positive numerical index, even if it is not an integer.]==]
function export.maxIndex(t)
	local max = 0
	for k in pairs(t) do
		if k > max then
			max = k
		end
	end
	return is_positive_integer(max) and max or 0
end

--[==[
This takes an array with one or more nil values, and removes the nil values
while preserving the order, so that the array can be safely traversed with
ipairs.
]==]
function export.compressSparseArray(t)
	local ret = {}
	local index = 1
	local nums = export.numKeys(t)
	for _, num in ipairs(nums) do
		ret[index] = t[num]
		index = index + 1
	end
	return ret
end

--[==[
A pairs iterator which respects any {{lua|__index}} metamethods that are tables, then falls back to the __pairs metamethod (if available).

Note: this function relies on the {{lua|getmetatable}} in-built function, which means it will return incorrect results if a metatable contains a {{lua|__metatable}} key, since that causes {{lua|getmetatable}} to return the value of {{lua|__metatable}} instead of the true metatable. Note, however, that the {{lua|__metatable}} key is sometimes set to the actual metatable, which is a common idiom for disabling {{lua|setmetatable}} without hiding the metatable itself. This is used by {{lua|mw.loadData}}, for instance.]==]
function export.indexPairs(t)
	-- Memoize keys with `seen_k`, as keys should never repeat, and memoize tables with `seen_t` to prevent infinite loops.
	local state, seen_k, seen_t, iter = t, {}, {}
	
	local function pairsfunc(_, k)
		local v
		if iter then
			-- Catch values in a table, since __pairs metamethods can return an arbitrary number of values.
			repeat
				v = {iter(state, k)}
			until not seen_k[v[1]]
			return unpack(v)
		end
		repeat
			k, v = next(state, k)
		until not seen_k[k]
		if k ~= nil then
			seen_k[k] = true
			return k, v
		end
		state = getmetatable(state)
		-- If there's a metatable with an __index table that hasn't been seen before, iterate over that.
		if type(state) == "table" then
			state = rawget(state, "__index")
			if type(state) == "table" and not seen_t[state] then
				seen_t[state], k = true
				return pairsfunc(_, k)
			end
		end
		-- Otherwise, use the __pairs metamethod of the original table.
		local mt = getmetatable(t)
		if not mt then
			return nil
		end
		-- Confirm there's a metamethod, to avoid pointless extra iteration, and that it's not `indexPairs`, to avoid an infinite loop.
		local __pairs = rawget(mt, "__pairs")
		if not __pairs or __pairs == export.indexPairs then
			return nil
		end
		-- Set `iter`, `state` and `k` using the metamethod, then iterate again.
		iter, state, k = __pairs(t)
		return pairsfunc(_, k)
	end
	
	return pairsfunc, state, nil
end

do
	local function _ipairs(t, i)
		i = i + 1
		local v = t[i]
		if v ~= nil then
			return i, v
		end
		return
	end
	
	--[==[
	An ipairs iterator which respects the {{lua|__index}} metamethod.]==]
	function export.indexIpairs(t)
		return _ipairs, t, 0
	end
end

--[==[
This is an iterator for sparse arrays. It can be used like ipairs, but can handle nil values.]==]
function export.sparseIpairs(t)
	local nums = export.numKeys(t)
	local i = 0
	return function()
		i = i + 1
		local key = nums[i]
		if key then
			return key, t[key]
		else
			return nil, nil
		end
	end
end

--[==[
This returns the size of a key/value pair table. For arrays, it is more efficient to use `export.length`.]==]
function export.size(t)
	local i = 0
	for _ in pairs(t) do
		i = i + 1
	end
	return i
end

--[==[
This returns the length of a table, or the first integer key n counting from 1 such that t[n + 1] is nil. It is a more reliable form of the operator #, which can become unpredictable under certain circumstances, and therefore should not be used when dealing with arbitrary inputs. This mainly occurs when metamethods are involved (e.g. with data loaded via mw.loadData), but can occur in other circumstances too, due to how Lua's implementation of tables works under the hood.]==]
function export.length(t)
	local i = 0
	repeat
		i = i + 1
	until t[i] == nil
	return i - 1
end
length = export.length


do
	local function is_equivalent(a, b, memo, include_mt)
		-- Raw equality check.
		if rawequal(a, b) then
			return true
		-- If not equal, a and b can only be equivalent if they're both tables.
		elseif not (type(a) == "table" and type(b) == "table") then
			return false
		end
		-- If a and b have been compared before, they must be equivalent.
		local memo_a = memo[a]
		if not memo_a then
			memo[a] = {[b] = true}
		elseif memo_a[b] then
			return true
		else
			memo_a[b] = true
		end
		local memo_b = memo[b]
		if not memo_b then
			memo[b] = {[a] = true}
		else -- We know memo_b won't have a, since memo_a didn't have b.
			memo_b[a] = true
		end
		-- If include_mt is set, check the metatables are equivalent.
		if (
			include_mt and
			not is_equivalent(getmetatable(a), getmetatable(b), memo, true)
		) then
			return false
		end
		-- Fast check: iterate over keys in a with `next` (which circumvents metamethods), checking if an equivalent value exists at the same key in b. Any tables-as-keys are set aside for the laborious check instead.
		local tablekeys_a, tablekeys_b, kb
		for ka, va in next, a do
			if type(ka) == "table" then
				if not tablekeys_a then
					tablekeys_a = {[ka] = va}
				else
					tablekeys_a[ka] = va
				end
			else
				local vb = rawget(b, ka)
				-- Faster to avoid recursion if possible, as we know va is not nil.
				if vb == nil or not is_equivalent(va, vb, memo, include_mt) then
					return false
				end
			end
			-- Iterate over b with `next` simultaneously, to check it's the same size and to grab any tables-as-keys for the laborious check, but also separately, since it might iterate in a different order, as this is unpredictable in Lua.
			local vb
			kb, vb = next(b, kb)
			-- Fail if b runs out of key/value pairs too early.
			if kb == nil then
				return false
			elseif type(kb) == "table" then
				if not tablekeys_b then
					tablekeys_b = {[kb] = vb}
				else
					tablekeys_b[kb] = vb
				end
			end
		end
		-- Fail if there are too many key/value pairs in b.
		if next(b, kb) ~= nil then
			return false
		-- If tablekeys_a == tablekeys_b they must be both nil, meaning there are no tables-as-keys to check, so success.
		elseif tablekeys_a == tablekeys_b then
			return true
		-- If only one them exists, then the tables can't be equivalent.
		elseif not (tablekeys_a and tablekeys_b) then
			return false
		end
		-- Laborious check: for each table-as-key in tablekeys_a, iterate over the pool in tablekeys_b looking for an equivalent key/value pair. If one if found, end the search and remove the match from tablekeys_b, to ensure one-to-one correspondence. If all keys in tablekeys_a match, tablekeys_b will be empty if the two are equivalent.
		for ka, va in next, tablekeys_a do
			local kb
			while true do
				local vb
				kb, vb = next(tablekeys_b, kb)
				-- Fail if tablekeys_b runs out of keys, as ka still hasn't matched.
				if kb == nil then
					return false
				-- Keys and values must both be equivalent.
				elseif (
					is_equivalent(ka, kb, memo, include_mt) and
					is_equivalent(va, vb, memo, include_mt)
				) then
					-- Remove matched key from the pool.
					tablekeys_b[kb] = nil
					break
				end
			end
		end
		-- Success iff tablekeys_b is now empty.
		return next(tablekeys_b) == nil
	end

	--[==[
	Recursively compare two values that may be tables, and returns true if all key-value pairs are structurally equivalent. Note that this handles arbitrary nesting of subtables (including recursive nesting) to any depth, for keys as well as values.

	If `include_mt` is true, then metatables are also compared.]==]
	function export.deepEquals(a, b, include_mt)
		return is_equivalent(a, b, {}, include_mt)
	end
end

do
	local function get_nested(t, k, ...)
		if t == nil then
			return nil
		elseif select("#", ...) ~= 0 then
			return get_nested(t[k], ...)
		end
		return t[k]
	end

	--[==[
	Given a table and an arbitrary number of keys, will successively access subtables using each key in turn, returning the value at the final key. For example, if {t} is { {[1] = {[2] = {[3] = "foo"}}}}, {export.getNested(t, 1, 2, 3)} will return {"foo"}.

	If no subtable exists for a given key value, returns nil, but will throw an error if a non-table is found at an intermediary key.
	]==]
	function export.getNested(t, ...)
		if t == nil or select("#", ...) == 0 then
			error("Must provide a table and at least one key.")
		end
		return get_nested(t, ...)
	end
end

do
	local function set_nested(t, v, k, ...)
		if select("#", ...) == 0 then
			t[k] = v
			return
		end
		local next_t = t[k]
		if next_t == nil then
			-- If there's no next table while setting nil, there's nothing more to do.
			if v == nil then
				return
			end
			next_t = {}
			t[k] = next_t
		end
		return set_nested(next_t, v, ...)
	end

	--[==[
	Given a table, value and an arbitrary number of keys, will successively access subtables using each key in turn, and sets the value at the final key. For example, if {t} is { {} }, {export.setNested(t, "foo", 1, 2, 3)} will modify {t} to { {[1] = {[2] = {[3] = "foo"} } } }.

	If no subtable exists for a given key value, one will be created, but the function will throw an error if a non-table value is found at an intermediary key.

	Note: the parameter order (table, value, keys) differs from functions like rawset, because the number of keys can be arbitrary. This is to avoid situations where an additional argument must be appended to arbitrary lists of variables, which can be awkward and error-prone: for example, when handling variable arguments ({{lua|...}}) or function return values.
	]==]
	function export.setNested(t, ...)
		if t == nil or select("#", ...) < 2 then
			error("Must provide a table and at least one key.")
		end
		return set_nested(t, ...)
	end
end

--[==[
Given a list and a value to be found, return true if the value is in the array portion of the list. Comparison is by value, using `deepEquals`.]==]
function export.contains(list, x, options)
	if options and options.key then
		x = options.key(x)
	end
	for _, v in ipairs(list) do
		if options and options.key then
			v = options.key(v)
		end
		if export.deepEquals(v, x) then return true end
	end
	return false
end

--[==[
Given a general table and a value to be found, return true if the value is in
either the array or hashmap portion of the table. Comparison is by value, using
`deepEquals`.

NOTE: This used to do shallow comparison by default and accepted a third
"deepCompare" param to do deep comparison. This param is still accepted but now
ignored.
]==]
function export.tableContains(tbl, x)
	for _, v in pairs(tbl) do
		if export.deepEquals(v, x) then return true end
	end
	return false
end

--[==[
Given a `list` and a `new_item` to be inserted, append the value to the end of the list if not already present
(or insert at an arbitrary position, if `options.pos` is given; see below). Comparison is by value, using {deepEquals}.

`options` is an optional table of additional options to control the behavior of the operation. The following options are
recognized:
* `pos`: Position at which insertion happens (i.e. before the existing item at position `pos`).
* `key`: Function of one argument to return a comparison key, as with {deepEquals}. The key function is applied to both
		 `item` and the existing item in `list` to compare against, and the comparison is done against the results.
		 This is useful when inserting a complex structure into an existing list while avoiding duplicates.
* `combine`: Function of three arguments (the existing item, the new item and the position, respectively) to combine an
			 existing item with `new_item`, when `new_item` is found in `list`. If unspecified, the existing item is
			 left alone.

Return {false} if entry already found, {true} if inserted.

For compatibility, `pos` can be specified directly as the third argument in place of `options`, but this is not
recommended for new code.

NOTE: This function is O(N) in the size of the existing list. If you use this function in a loop to insert several
items, you will get O(M*(M+N)) behavior, effectively O((M+N)^2). Thus it is not recommended to use this unless you are
sure the total number of items will be small. (An alternative for large lists is to insert all the items without
checking for duplicates, and use {removeDuplicates()} at the end.)
]==]
function export.insertIfNot(list, new_item, options)
	if type(options) == "number" then
		options = {pos = options}
	end
	if options and options.combine then
		local new_item_key
		-- Don't use options.key and options.key(new_item) or new_item in case the key is legitimately false or nil.
		if options.key then
			new_item_key = options.key(new_item)
		else
			new_item_key = new_item
		end
		for i, item in ipairs(list) do
			local item_key
			if options.key then
				item_key = options.key(item)
			else
				item_key = item
			end
			if export.deepEquals(item_key, new_item_key) then
				local retval = options.combine(item, new_item, i)
				if retval ~= nil then
					list[i] = retval
				end
				return false
			end
		end
	elseif export.contains(list, new_item, options) then
		return false
	end
	if options and options.pos then
		insert(list, options.pos, new_item)
	else
		insert(list, new_item)
	end
end

--[==[
Finds key for specified value in a given table. Roughly equivalent to reversing the key-value pairs in the table:
* {reversed_table = { [value1] = key1, [value2] = key2, ... }}
and then returning {reversed_table[valueToFind]}.

The value can only be a string or a number (not nil, a boolean, a table, or a function).

Only reliable if there is just one key with the specified value. Otherwise, the function returns the first key found,
and the output is unpredictable.
]==]
function export.keyFor(t, valueToFind)
	for key, value in pairs(t) do
		if value == valueToFind then
			return key
		end
	end
	return nil
end

do
	-- The default sorting function used in export.keysToList if no keySort is defined.
	local function defaultKeySort(key1, key2)
		-- "number" < "string", so numbers will be sorted before strings.
		local type1, type2 = type(key1), type(key2)
		if type1 ~= type2 then
			return type1 < type2
		end
		-- string_sort fixes a bug in < whereby all codepoints above U+FFFF are treated as equal.
		return string_sort(key1, key2)
	end

	--[==[
	Return a list of the keys in a table, sorted using either the default table.sort function or a custom keySort function.
	If there are only numerical keys, numKeys is probably more efficient.
	]==]
	function export.keysToList(t, keySort)
		local list, i = {}, 0
		for key in pairs(t) do
			i = i + 1
			list[i] = key
		end
		-- Use specified sort function, or otherwise defaultKeySort.
		sort(list, keySort or defaultKeySort)
		return list
	end
	keys_to_list = export.keysToList
end

--[==[
Iterates through a table, with the keys sorted using the keysToList function. If there are only numerical keys,
sparseIpairs is probably more efficient.
]==]
function export.sortedPairs(t, keySort)
	local list, i = keys_to_list(t, keySort, true), 0

	return function()
		i = i + 1
		local key = list[i]
		if key ~= nil then
			return key, t[key]
		end
	end
end

do
	local function iter(t, i)
		i = i - 1
		if i > 0 then
			return i, t[i]
		end
	end

	function export.reverseIpairs(t)
		-- Not safe to use #t, as it can be unpredictable if there is a hash part.
		return iter, t, length(t) + 1
	end
end

local function getIteratorValues(i, j , s, list)
	i = (i and i < 0 and #list - i + 1) or i or (s and s < 0 and #list) or 1
	j = (j and j < 0 and #list - j + 1) or j or (s and s < 0 and 1) or #list
	s = s or (j < i and -1) or 1
	if (
		i == 0 or i % 1 ~= 0 or
		j == 0 or j % 1 ~= 0 or
		s == 0 or s % 1 ~= 0
	) then
		error("Arguments i, j and s must be non-zero integers.")
	end
	return i, j, s
end

--[==[
Given an array `list` and function `func`, iterate through the array applying {func(r, k, v)}, and returning the result,
where `r` is the value calculated so far, `k` is an index, and `v` is the value at index `k`. For example,
{reduce(array, function(a, b) return a + b end)} will return the sum of `array`.

Optional arguments:
* `i`: start index; negative values count from the end of the array
* `j`: end index; negative values count from the end of the array
* `s`: step increment
These must be non-zero integers. The function will determine where to iterate from, whether to iterate forwards or
backwards and by how much, based on these inputs (see examples below for default behaviours).

Examples:
# No values for i, j or s results in forward iteration from the start to the end in steps of 1 (the default).
# s=-1 results in backward iteration from the end to the start in steps of 1.
# i=7, j=3 results in backward iteration from indices 7 to 3 in steps of 1 (i.e. s=-1).
# j=-3 results in forward iteration from the start to the 3rd last index.
# j=-3, s=-1 results in backward iteration from the end to the 3rd last index.
Note: directionality generally only matters for `reduce`, but values of s > 1 (or s < -1) still affect the return value
of `apply`.
]==]

function export.reduce(list, func, i, j, s)
	i, j, s = getIteratorValues(i, j , s, list)
	local ret = list[i]
	for k = i + s, j, s do
		ret = func(ret, k, list[k])
	end
	return ret
end

--[==[
Given an array `list` and function `func`, iterate through the array applying {func(k, v)} (where `k` is an index, and
`v` is the value at index `k`), and return an array of the resulting values. For example,
{apply(array, function(a) return 2*a end)} will return an array where each member of `array` has been doubled.

Optional arguments:
* `i`: start index; negative values count from the end of the array
* `j`: end index; negative values count from the end of the array
* `s`: step increment
These must be non-zero integers. The function will determine where to iterate from, whether to iterate forwards or
backwards and by how much, based on these inputs (see examples below for default behaviours).

Examples:
# No values for i, j or s results in forward iteration from the start to the end in steps of 1 (the default).
# s=-1 results in backward iteration from the end to the start in steps of 1.
# i=7, j=3 results in backward iteration from indices 7 to 3 in steps of 1 (i.e. s=-1).
# j=-3 results in forward iteration from the start to the 3rd last index.
# j=-3, s=-1 results in backward iteration from the end to the 3rd last index.
Note: directionality makes the most difference for `reduce`, but values of s > 1 (or s < -1) still affect the return
value of `apply`.
]==]
function export.apply(list, func, i, j, s)
	local modified_list = export.deepcopy(list)
	i, j, s = getIteratorValues(i, j , s, modified_list)
	for k = i, j, s do
		modified_list[k] = func(k, modified_list[k])
	end
	return modified_list
end

--[==[
Given an array `list` and function `func`, iterate through the array applying {func(k, v)} (where `k` is an index, and
`v` is the value at index `k`), and returning whether the function is true for all iterations.

Optional arguments:
* `i`: start index; negative values count from the end of the array
* `j`: end index; negative values count from the end of the array
* `s`: step increment
These must be non-zero integers. The function will determine where to iterate from, whether to iterate forwards or
backwards and by how much, based on these inputs (see examples below for default behaviours).

Examples:
# No values for i, j or s results in forward iteration from the start to the end in steps of 1 (the default).
# s=-1 results in backward iteration from the end to the start in steps of 1.
# i=7, j=3 results in backward iteration from indices 7 to 3 in steps of 1 (i.e. s=-1).
# j=-3 results in forward iteration from the start to the 3rd last index.
# j=-3, s=-1 results in backward iteration from the end to the 3rd last index.
]==]
function export.all(list, func, i, j, s)
	i, j, s = getIteratorValues(i, j , s, list)
	local ret = true
	for k = i, j, s do
		ret = ret and not not (func(k, list[k]))
		if not ret then break end
	end
	return ret
end

--[==[
Given an array `list` and function `func`, iterate through the array applying {func(k, v)} (where `k` is an index, and
`v` is the value at index `k`), and returning whether the function is true for at least one iteration.

Optional arguments:
* `i`: start index; negative values count from the end of the array
* `j`: end index; negative values count from the end of the array
* `s`: step increment
These must be non-zero integers. The function will determine where to iterate from, whether to iterate forwards or
backwards and by how much, based on these inputs (see examples below for default behaviours).

Examples:
# No values for i, j or s results in forward iteration from the start to the end in steps of 1 (the default).
# s=-1 results in backward iteration from the end to the start in steps of 1.
# i=7, j=3 results in backward iteration from indices 7 to 3 in steps of 1 (i.e. s=-1).
# j=-3 results in forward iteration from the start to the 3rd last index.
# j=-3, s=-1 results in backward iteration from the end to the 3rd last index.
]==]
function export.any(list, func, i, j, s)
	i, j, s = getIteratorValues(i, j , s, list)
	local ret = false
	for k = i, j, s do
		ret = ret or not not (func(k, list[k]))
		if ret then break end
	end
	return ret
end

--[==[
Joins an array with serial comma and serial conjunction, normally {"and"}. An improvement on {mw.text.listToText},
which doesn't properly handle serial commas.

Options:
* `conj`: Conjunction to use; defaults to {"and"}.
* `italicizeConj`: Italicize conjunction: for [[Module:also]]
* `dontTag`: Don't tag the serial comma and serial {"and"}. For error messages, in which HTML cannot be used.
]==]
function export.serialCommaJoin(seq, options)
	local length = #seq

	if not options then
		options = {}
	end

	local conj
	if length > 1 then
		conj = options.conj or "and"
		if options.italicizeConj then
			conj = "''" .. conj .. "''"
		end
	end

	if length == 0 then
		return ""
	elseif length == 1 then
		return seq[1] -- nothing to join
	elseif length == 2 then
		return seq[1] .. " " .. conj .. " " .. seq[2]
	else
		local punc = options.punc or ","
		local comma = options.dontTag and punc or "<span class=\"serial-comma\">" .. punc .. "</span>"
		conj = options.dontTag and " " .. conj .. " " or "<span class=\"serial-and\"> " .. conj .. "</span> "
		return concat(seq, punc .. " ", 1, length - 1) ..
				comma .. conj .. seq[length]
	end
end

--[==[
Concatenate all values in the table that are indexed by a number, in order.
* {sparseConcat{ a, nil, c, d }}  =>  {"acd"}
* {sparseConcat{ nil, b, c, d }}  =>  {"bcd"}
]==]
function export.sparseConcat(t, sep, i, j)
	local list = {}

	local list_i = 0
	for _, v in export.sparseIpairs(t) do
		list_i = list_i + 1
		list[list_i] = v
	end

	return concat(list, sep, i, j)
end

--[==[
Values of numeric keys in array portion of table are reversed: { { "a", "b", "c" }} -> { { "c", "b", "a" }}
]==]
function export.reverse(t)
	-- Not safe to use #t, as it can be unpredictable if there is a hash part.
	local ret, base = {}, 0
	repeat
		base = base + 1
	until t[base] == nil
	for i = base - 1, 1, -1 do
		ret[base - i] = t[i]
	end
	return ret
end

function export.reverseConcat(t, sep, i, j)
	return concat(export.reverse(t), sep, i, j)
end

--[==[
Invert an array. For example, {invert({ "a", "b", "c" })} -> { { a = 1, b = 2, c = 3 }}
]==]
function export.invert(array)
	local map = {}
	for i, v in ipairs(array) do
		map[v] = i
	end
	return map
end

--[==[
Convert `list` (a table with a list of values) into a set (a table where those values are keys instead). This is a useful
way to create a fast lookup table, since looking up a table key is much, much faster than iterating over the whole list
to see if it contains a given value.

By default, each item is given the value true. If the optional parameter `value` is a function or functor, then the value
for each item is determined by calling it with the item key as the first parameter, plus any additional arguments passed
to {listToSet}; if value is anything else, then it is used as the fixed value for every item.
]==]
function export.listToSet(list, value, ...)
	local set, i = {}, 0
	if value == nil then
		value = true
	else
		if is_callable(value) then
			-- Separate loop avoids an "is callable" lookup each iteration.
			while true do
				i = i + 1
				local item = list[i]
				if item == nil then
					return set
				end
				set[item] = value(item, ...)
			end
		end
	end
	while true do
		i = i + 1
		local item = list[i]
		if item == nil then
			return set
		end
		set[item] = value
	end
end

--[==[
Return true if all keys in the table are consecutive integers starting at 1.
]==]
function export.isArray(t)
	local i = 0
	for _ in pairs(t) do
		i = i + 1
		if t[i] == nil then
			return false
		end
	end
	return true
end

--[==[
Add a list of aliases for a given key to a table. The aliases must be given as a table.
]==]
function export.alias(t, k, aliases)
	for _, alias in pairs(aliases) do
		t[alias] = t[k]
	end
end

return export