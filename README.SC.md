lldbinit-arm
===
实现类似gdbinit的功能，基于lldbinit的修改，主要是原来的项目...太不爽。

[English](https://github.com/ipfans/lldbinit-arm/blob/master/README.md)

x86_64:

![lldbinit-arm x86_64](http://ww2.sinaimg.cn/large/69e37fdbgw1efu4mcssfej20ze0d50w9.jpg)

ARM:
![lldbinit-arm arm](http://ww4.sinaimg.cn/large/69e37fdbgw1efu7wuaga4j20pr0kjtfm.jpg)

如何安装
---
下载zip文件，并且将py文件复制到:
```
cp lldbinit.py /Library/Python/2.7/site-packages
```

在用户$HOME/.lldbinit文件中添加(没有就创建):
```
command script import lldbinit
```

帮助
---
实现的命令如下

```
	stepo			- 步过指令 (call/movs/stos/cmps/loop)
	dd 				- 显示指定地址的内存
   	ctx/context		- 现实当前寄存器和反汇编内容(一般不需要要，中断时会自动显示)
	lb	    		- 从文件中加载断点并应用	 
	u 				- 反汇编指定地址
	ddword	    	- dump data as dword 
	dq	    		- dump data as qword
	dw	    		- dump data as word
	iphone	    	- 连接到iPhone
	info			- 像gdb一样显示动态库加载地址
	sbr				- 智能根据偏移下断点，忽视ASLR。
```

像获取单一命令帮助，请使用如下命令

```
(lldb) script help(lldbinit.dd)
Help on function dd in module lldbinit:

dd(debugger, command, result, dict)
    dump hex data at certain address.
    
    Example:
        dd 0x100000ef0
```
