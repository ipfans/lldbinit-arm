lldbinit-arm
===
Similar implementation of .gdbinit from fG! for lldb in python. Based on lldbinit.

[中文说明](https://github.com/ipfans/lldbinit-arm/blob/master/README.SC.md)

x86_64:

![lldbinit-arm x86_64](http://ww2.sinaimg.cn/large/69e37fdbgw1efu4mcssfej20ze0d50w9.jpg)

ARM:
![lldbinit-arm arm](http://ww4.sinaimg.cn/large/69e37fdbgw1efu7wuaga4j20pr0kjtfm.jpg)

Install
---
How to install it:
```
cp lldbinit.py /Library/Python/2.7/site-packages
```

in $HOME/.lldbinit add:
```
command script import lldbinit
```

Help
---
Commands which are implemented:

```
	stepo			- step over some instructions (call/movs/stos/cmps/loop)
	dd 				- dump hex data at certain address (keep compatibility with .gdbinit)
   	      			this shoud be db command
   	ctx/context		- dump registers and assembly
	lb	    		- load breakpoints from file and apply them (currently only func names are applied)	 	
	u 				- dump instructions at certain address (SoftICE like u command style)
	ddword	    	- dump data as dword 
	dq	    		- dump data as qword
	dw	    		- dump data as word
	iphone	    	- connect to debugserver running on iPhone
	info			- show shared library info like gdb
	sbr				- smart breakpoint to ignore ASLR. Need offset to set bp.
```

If you wanna inline help, just try this:

```
(lldb) script help(lldbinit.dd)
Help on function dd in module lldbinit:

dd(debugger, command, result, dict)
    dump hex data at certain address.
    
    Example:
        dd 0x100000ef0
```
