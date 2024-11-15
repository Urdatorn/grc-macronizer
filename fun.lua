local export = {}

local format = string.format
local getmetatable = getmetatable
local gmatch = string.gmatch
local ipairs = ipairs
local is_callable -- defined as export.is_callable below
local pairs = pairs
local select = select
local tostring = tostring
local type = type
local unpack = unpack

local function _iterString(iter, i)
	i = i + 1
	local char = iter()
	if char ~= nil then
		return i, char
	end
end

-- Iterate over UTF-8-encoded codepoints in string.
local function iterString(str)
	return _iterString, gmatch(str, ".[\128-\191]*"), 0
end

--[==[
Return {true} if the input is a function or functor (a table which can be called like a function, because it has a {__call} metamethod).
]==]
function export.is_callable(f)
	local f_type = type(f)
	if f_type == "function" then
		return true
	elseif f_type ~= "table" then
		return false
	end
	local mt = getmetatable(f)
	-- __call metamethods have to be functions, not functors.
	return mt and type(mt.__call) == "function" or false
end
is_callable = export.is_callable

function export.chain(func1, func2, ...)
	return func1(func2(...))
end

--	map(function(number) return number ^ 2 end,
--		{ 1, 2, 3 })									--> { 1, 4, 9 }
--	map(function (char) return string.char(string.byte(char) - 0x20) end,
--		"abc")											--> { "A", "B", "C" }
function export.map(func, iterable, isArray)
	local array = {}
	for k, v in (type(iterable) == "string" and iterString or (isArray or iterable[1] ~= nil) and ipairs or pairs)(iterable) do
		array[k] = func(v, k, iterable)
	end
	return array
end

function export.mapIter(func, iter, iterable, initVal)
	-- initVal could be anything
	local array, i = {}, 0
	for x, y in iter, iterable, initVal do
		i = i + 1
		array[i] = func(y, x, iterable)
	end
	return array
end

function export.forEach(func, iterable, isArray)
	for k, v in (type(iterable) == "string" and iterString or (isArray or iterable[1] ~= nil) and ipairs or pairs)(iterable) do
		func(v, k, iterable)
	end
	return nil
end

-------------------------------------------------
-- From http://lua-users.org/wiki/CurriedLua
-- reverse(...) : take some tuple and return a tuple of elements in reverse order
--
-- e.g. "reverse(1,2,3)" returns 3,2,1
local function reverse(...)
	-- reverse args by building a function to do it, similar to the unpack() example
	local function reverseHelper(acc, v, ...)
		if select('#', ...) == 0 then
			return v, acc()
		else
			return reverseHelper(function() return v, acc() end, ...)
		end
	end
	
	-- initial acc is the end of the list
	return reverseHelper(function() return end, ...)
end

function export.curry(func, numArgs)
	-- currying 2-argument functions seems to be the most popular application
	numArgs = numArgs or 2
	
	-- no sense currying for 1 arg or less
	if numArgs <= 1 then return func end
	
	-- helper takes an argTrace function, and number of arguments remaining to be applied
	local function curryHelper(argTrace, n)
		if n == 0 then
			-- kick off argTrace, reverse argument list, and call the original function
			return func(reverse(argTrace()))
		else
			-- "push" argument (by building a wrapper function) and decrement n
			return function(onearg)
				return curryHelper(function() return onearg, argTrace() end, n - 1)
			end
		end
	end
	
	-- push the terminal case of argTrace into the function first
	return curryHelper(function() return end, numArgs)
end

-------------------------------------------------

--	some(function(val) return val % 2 == 0 end,
--		{ 2, 3, 5, 7, 11 })						--> true
function export.some(func, t, isArray)
	for k, v in ((isArray or t[1] ~= nil) and ipairs or pairs)(t) do
		if func(v, k, t) then
			return true
		end
	end
	return false
end

--	all(function(val) return val % 2 == 0 end,
--		{ 2, 4, 8, 10, 12 })					--> true
function export.all(func, t, isArray)
	for k, v in ((isArray or t[1] ~= nil) and ipairs or pairs)(t) do
		if not func(v, k, t) then
			return false
		end
	end
	return true
end

function export.filter(func, t, isArray)
	local new_t = {}
	if isArray or t[1] ~= nil then -- array
		local new_i = 0
		for i, v in ipairs(t) do
			if func(v, i, t) then
				new_i = new_i + 1
				new_t[new_i] = v
			end
		end
	else
		for k, v in pairs(t) do
			if func(v, k, t) then
				new_t[k] = v -- or create array?
			end
		end
	end
	return new_t
end

function export.fold(func, t, accum)
	for i, v in ipairs(t) do
		accum = func(accum, v, i, t)
	end
	return accum
end


-------------------------------
-- Fancy stuff
local function capture(...)
	local vals = { n = select('#', ...), ... }
	return function()
		return unpack(vals, 1, vals.n)
	end
end

-- Log input and output of function.
-- Receives a function and returns a modified form of that function.
function export.logReturnValues(func, prefix)
	return function(...)
		local inputValues = capture(...)
		local returnValues = capture(func(...))
		if prefix then
			mw.log(prefix, inputValues())
			mw.log(returnValues())
		else
			mw.log(inputValues())
			mw.log(returnValues())
		end
		return returnValues()
	end
end

export.log = export.logReturnValues

-- Convenience function to make all functions in a table log their input and output.
function export.logAll(t)
	for k, v in pairs(t) do
		if type(v) == "function" then
			t[k] = export.logReturnValues(v, tostring(k))
		end
	end
	return t
end

----- M E M O I Z A T I O N-----
-- Memoizes a function or callable table.
-- Supports any number of arguments and return values.
-- If the optional parameter `simple` is set, then the memoizer will use a faster implementation, but this is only compatible with one argument and one return value. If `simple` is set, additional arguments will be accepted, but this should only be done if those arguments will always be the same.
do
	-- Sentinels.
	local args, nil_, neg_0, pos_nan, neg_nan
	
	-- Since all possible inputs need to be memoized (including true, false and nil), the table of arguments is stored with the sentinel key `args`. In addition, certain values can't be used as table keys, so they require sentinels as well: e.g. f("foo", nil, "bar") would be memoized at f["foo"][nil_]["bar"][args]. These values are:
		-- nil.
		-- -0, which is equivalent to 0 in most situations, but becomes "-0" on conversion to string; it also behaves differently in some operations (e.g. 1/a evaluates to inf if a is 0, but -inf if a is -0).
		-- NaN and -NaN, which are the only values for which n == n is false; they only seem to differ on conversion to string ("nan" and "-nan").
	local function get_key(input)
		-- nil
		if input == nil then
			if not nil_ then
				nil_ = {}
			end
			return nil_
		-- -0
		elseif input == 0 and 1 / input < 0 then
			if not neg_0 then
				neg_0 = {}
			end
			return neg_0
		-- Default
		elseif input == input then
			return input
		-- NaN
		elseif format("%f", input) == "nan" then
			if not pos_nan then
				pos_nan = {}
			end
			return pos_nan
		-- -NaN
		elseif not neg_nan then
			neg_nan = {}
		end
		return neg_nan
	end
	
	-- Return values are memoized as tables of return values, which are looked up using each input argument as a key, followed by args. e.g. if the input arguments were (1, 2, 3), the memo would be located at t[1][2][3][args]. args is always used as the final lookup key so that (for example) the memo for f(1, 2, 3), f[1][2][3][args], doesn't interfere with the memo for f(1, 2), f[1][2][args].
	local function get_memo(memo, n, nargs, key, ...)
		key = get_key(key)
		local next_memo = memo[key]
		if next_memo == nil then
			next_memo = {}
			memo[key] = next_memo
		end
		memo = next_memo
		return n == nargs and memo or get_memo(memo, n + 1, nargs, ...)
	end
	
	-- Catch the function output values, and return the hidden variable arg (which is {...}, and available when a function has ...). We do this instead of catching the output in a table directly, because arg also contains the key "n", which is equal to select("#", ...). i.e. it's the number of arguments in ..., including any nils returned after the last non-nil value (e.g. select("#", nil) == 1, select("#") == 0, select("#", nil, "foo", nil, nil) == 4 etc.). The distinction between nil and nothing affects some native functions (e.g. tostring() throws an error, but tostring(nil) returns "nil"), so it needs to be reconstructable from the memo.
	local function catch_output(...)
		return arg
	end
	
	function export.memoize(func, simple)
		if not is_callable(func) then
			local _type = type(func)
			error(format(
				"Only functions and callable tables are memoizable. Received %s.",
				 _type == "table" and "non-callable table" or _type
			 ))
		end
		local memo = {}
		return simple and function(...)
			local key = get_key(...)
			local output = memo[key]
			if output ~= nil then
				if output == nil_ then
					return nil
				end
				return output
			end
			output = func(...)
			if output ~= nil then
				memo[key] = output
				return output
			elseif not nil_ then
				nil_ = {}
			end
			memo[key] = nil_
			return nil
		end or function(...)
			local nargs = select("#", ...)
			local memo = nargs == 0 and memo or get_memo(memo, 1, nargs, ...)
			if not args then
				args = {}
			end
			local output = memo[args]
			if output == nil then
				output = catch_output(func(...))
				memo[args] = output
			end
			-- Unpack from 1 to the original number of return values (memoized as output.n); unpack returns nil for any values not in output.
			return unpack(output, 1, output.n)
		end
	end
end

return export