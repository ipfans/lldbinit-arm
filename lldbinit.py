#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
    Similar implementation of .gdbinit from fG! for lldb in python

    How to install it:
    cp lldbinit.py /Library/Python/2.7/site-packages
    in $HOME/.lldbinit add:
    command script import lldbinit

    Apple's default lldb comes with annoying disassembly eg:
    -> 0x1d70:  push   EBP
           0x1d71:  mov    EBP, ESP
           0x1d73:  push   EDI
           0x1d74:  push   ESI
           0x1d75:  sub    ESP, 80

    with lldb from lldb svn:

    -> 0x1d70:  push   ebp
           0x1d71:  mov    ebp, esp
           0x1d73:  push   edi
           0x1d74:  push   esi
           0x1d75:  sub    esp, 0x50

    Somewhere nicer, to compile lldb from svn we need to do:
    svn co http://llvm.org/svn/llvm-project/lldb/trunk lldb
    xcodebuild -configuration Release

    From latest update of lldb there is change in handling IO, so to use
    this script and be compatible with Apple's lldb you need to checkout
    revision r200253 and you can do that by typing:
    svn co -r r200253 http://llvm.org/svn/llvm-project/lldb/trunk

Commands which are implemented:
    stepo       - step over some instructions (call/movs/stos/cmps/loop)
    dd          - dump hex data at certain address (keep compatibility with .gdbinit)
              this shoud be db command
    ctx/context - dump registers and assembly
    lb      - load breakpoints from file and apply them (currently only func names are applied)
    u       - dump instructions at certain address (SoftICE like u command style)
    ddword  - dump data as dword
    dq      - dump data as qword
    dw      - dump data as word

    hook-stop can be added only when target exists, before it's not possible (maybe in later versions
    of lldb it is or will be possible but...). Trick to get arround this is to create thread which will
    try to add hook-stop, and will continue doing so until it's done. This could cause some raise conditions
    as I don't know if this is thread safe, however in my testing (and using it) it worked quite well so
    I keep using it instead of adding extra command "init" or such when target is created...

    Currently registers dump are done for i386/x86_64 . ARM will be added when I find need for it, atm it's
    not required... (or when somebody else adds it)...

'''

if __name__ == "__main__":
    print("Run only as script from lldb... Not as standalone program")

try:
    import lldb
except:
    pass
import thread
import time
import struct

# i386 registers
old_eax = 0
old_ecx = 0
old_edx = 0
old_ebx = 0
old_esp = 0
old_ebp = 0
old_esi = 0
old_edi = 0
old_eip = 0
old_eflags = 0
old_cs = 0
old_ds = 0
old_fs = 0
old_gs = 0
old_ss = 0
old_es = 0

# x86_64 registers
old_rax = 0
old_rcx = 0
old_rdx = 0
old_rbx = 0
old_rsp = 0
old_rbp = 0
old_rsi = 0
old_rdi = 0
old_r8 = 0
old_r9 = 0
old_r10 = 0
old_r11 = 0
old_r12 = 0
old_r13 = 0
old_r14 = 0
old_r15 = 0
old_rflags = 0
old_rip = 0

# ARM32 registers
oldr0 = 0
oldr1 = 0
oldr2 = 0
oldr3 = 0
oldr4 = 0
oldr5 = 0
oldr6 = 0
oldr7 = 0
oldr8 = 0
oldr9 = 0
oldr10 = 0
oldr11 = 0
oldr12 = 0
oldsp = 0
oldlr = 0

BLACK = 0
RED = 1
GREEN = 2
YELLOW = 3
BLUE = 4
MAGENTA = 5
CYAN = 6
WHITE = 7

COLOR_REGNAME = GREEN
COLOR_REGVAL = WHITE
COLOR_REGVAL_MODIFIED = RED
COLOR_SEPARATOR = BLUE
COLOR_CPUFLAGS = RED
COLOR_HIGHLIGHT_LINE = CYAN
#stop-disassembly-count
#stop-disassembly-display
#frame-format
#thread-format
#prompt

GlobalListOutput = []

hook_stop_added = 0


def wait_for_hook_stop():
    while True:
        res = lldb.SBCommandReturnObject()
        handleCmd = lldb.debugger.GetCommandInterpreter().HandleCommand
        handleCmd("target stop-hook add -o \"HandleHookStopOnTarget\"", res)
        if res.Succeeded() is True:
            return
        time.sleep(0.05)


def __lldb_init_module(debugger, internal_dict):
    '''
        we can execute commands using debugger.HandleCommand which makes all outptu to default
        lldb console. With GetCommandinterpreter().HandleCommand() we can consume all output
        with SBCommandReturnObject and parse data before we send it to output (eg. modify it);
    '''
    global hook_stop_added

    '''
        If I'm running from $HOME where .lldbinit is located, seems like lldb will load
        .lldbinit 2 times, thus this dirty hack is here to prevent doulbe loading...
        if somebody knows better way, would be great to know :)
    '''
    var = lldb.debugger.GetInternalVariableValue("stop-disassembly-count", lldb.debugger.GetInstanceName())
    if var.IsValid():
        var = var.GetStringAtIndex(0)
        if var == "0":
            return
    res = lldb.SBCommandReturnObject()
    handleCmd = lldb.debugger.GetCommandInterpreter().HandleCommand
    handleCmd("settings set target.x86-disassembly-flavor intel", res)
    handleCmd("command script add -f lldbinit.stepo stepo", res)
    handleCmd("command script add -f lldbinit.HandleHookStopOnTarget HandleHookStopOnTarget", res)
    handleCmd("command script add -f lldbinit.dd dd", res)
    handleCmd("command script add -f lldbinit.si si", res)
    handleCmd("command script add -f lldbinit.c  c", res)
    handleCmd("command script add -f lldbinit.r  r", res)
    handleCmd("command script add -f lldbinit.r  run", res)
    handleCmd("command script add -f lldbinit.HandleHookStopOnTarget ctx", res)
    handleCmd("command script add -f lldbinit.HandleHookStopOnTarget context", res)
    handleCmd("command script add -f lldbinit.DumpInstructions u", res)
    handleCmd("command script add -f lldbinit.LoadBreakPoints lb", res)
    handleCmd("command script add -f lldbinit.dq dq", res)
    handleCmd("command script add -f lldbinit.ddword ddword", res)
    handleCmd("command script add -f lldbinit.dw dw", res)
    # handleCmd("command script add -f lldbinit.init init", res)
    # handleCmd("target stop-hook add -o \"HandleHookStopOnTarget\"", res)
    # if res.Succeeded() == True:
    #     hook_stop_added = 1
    # else:
    #     print("[*] hook-stop not initialized...")
    #     print("[*] type init once target is loaded...")
    # debugger.HandleCommand("target stop-hook add -o \"HandleHookStopOnTarget\"")
    '''
        target stop-hook can be added only when target is loaded, thus I create thread
        to execute this command until it returns success... dunno if this is ok, or thread
        safe, but I hate to add extra command "init" or such to install this hook...
    '''
    thread.start_new_thread(wait_for_hook_stop, ())

    handleCmd("settings set prompt \"\033[31m(lldb) \033[0m\"", res)
    # handleCmd("settings set frame-format \"\n\"", res)
    # handleCmd("settings set thread-format \"\"", res)
    handleCmd("settings set stop-disassembly-count 0", res)
    return


def get_arch():
    return lldb.debugger.GetSelectedTarget().triple.split('-')[0]


def get_frame():
    return lldb.debugger.GetSelectedTarget().process.selected_thread.GetSelectedFrame()


def is_i386():
    arch = get_arch()
    if arch[0:1] == "i":
        return True
    return False


def is_x64():
    arch = get_arch()
    if arch == "x86_64":
        return True
    return False


def is_arm32():
    arch = get_arch()
    if arch == "arm":
        return True
    return False


def color_reset():
    output("\033[0m")


def color_bold():
    output("\033[1m")


def color_underline():
    output("\033[4m")


def color(x):
    out_col = ""
    if x == BLACK:
        out_col = "\033[30m"
    elif x == RED:
        out_col = "\033[31m"
    elif x == GREEN:
        out_col = "\033[32m"
    elif x == YELLOW:
        out_col = "\033[33m"
    elif x == BLUE:
        out_col = "\033[34m"
    elif x == MAGENTA:
        out_col = "\033[35m"
    elif x == CYAN:
        out_col = "\033[36m"
    elif x == WHITE:
        out_col = "\033[37m"
    output(out_col)


def output(x):
    #sys.stdout.flush()
    #sys.stdout.write(x)
    #sys.stdout.flush()
    global GlobalListOutput
    #print("Adding to the list " + x)
    GlobalListOutput.append(x)


def get_register(reg_name):
    regs = get_GPRs()
    for reg in regs:
        if reg_name == reg.GetName():
            return reg.GetValue()
    return 0


def get_registers(kind):
    """
    Returns the registers given the frame and the kind of registers desired.

    Returns None if there's no such kind.
    """
    registerSet = get_frame().GetRegisters()  # Return type of SBValueList.
    for value in registerSet:
        if kind.lower() in value.GetName().lower():
            return value

    return None


def dump_eflags(eflags):
    if (eflags >> 0xB) & 1:
        output("O ")
    else:
        output("o ")

    if (eflags >> 0xA) & 1:
        output("D ")
    else:
        output("d ")

    if (eflags >> 9) & 1:
        output("I ")
    else:
        output("i ")

    if (eflags >> 8) & 1:
        output("T ")
    else:
        output("t ")

    if (eflags >> 7) & 1:
        output("S ")
    else:
        output("s ")

    if (eflags >> 6) & 1:
        output("Z ")
    else:
        output("z ")

    if (eflags >> 4) & 1:
        output("A ")
    else:
        output("a ")

    if (eflags >> 2) & 1:
        output("P ")
    else:
        output("p ")

    if eflags & 1:
        output("C")
    else:
        output("c")


def reg64():
    global old_cs
    global old_ds
    global old_fs
    global old_gs
    global old_ss
    global old_es
    global old_rax
    global old_rcx
    global old_rdx
    global old_rbx
    global old_rsp
    global old_rbp
    global old_rsi
    global old_rdi
    global old_r8
    global old_r9
    global old_r10
    global old_r11
    global old_r12
    global old_r13
    global old_r14
    global old_r15
    global old_rflags
    global old_rip

    rax = int(get_register("rax"), 16)
    rcx = int(get_register("rcx"), 16)
    rdx = int(get_register("rdx"), 16)
    rbx = int(get_register("rbx"), 16)
    rsp = int(get_register("rsp"), 16)
    rbp = int(get_register("rbp"), 16)
    rsi = int(get_register("rsi"), 16)
    rdi = int(get_register("rdi"), 16)
    r8 = int(get_register("r8"), 16)
    r9 = int(get_register("r9"), 16)
    r10 = int(get_register("r10"), 16)
    r11 = int(get_register("r11"), 16)
    r12 = int(get_register("r12"), 16)
    r13 = int(get_register("r13"), 16)
    r14 = int(get_register("r14"), 16)
    r15 = int(get_register("r15"), 16)
    rip = int(get_register("rip"), 16)
    rflags = int(get_register("rflags"), 16)
    cs = int(get_register("cs"), 16)
    gs = int(get_register("gs"), 16)
    fs = int(get_register("fs"), 16)
    #not needed as x64 doesn't use them...
    #ds = int(get_register("ds"), 16)
    #ss = int(get_register("ss"), 16)

    color(COLOR_REGNAME)
    output("  RAX: ")
    if rax == old_rax:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rax))
    old_rax = rax

    color(COLOR_REGNAME)
    output("  RBX: ")
    if rbx == old_rbx:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rbx))
    old_rbx = rbx

    color(COLOR_REGNAME)
    output("  RBP: ")
    if rbp == old_rbp:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rbp))
    old_rbp = rbp

    color(COLOR_REGNAME)
    output("  RSP: ")
    if rsp == old_rsp:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rsp))
    old_rsp = rsp

    output("  ")
    color_bold()
    color_underline()
    color(COLOR_CPUFLAGS)
    dump_eflags(rflags)
    color_reset()

    output("\n")

    color(COLOR_REGNAME)
    output("  RDI: ")
    if rdi == old_rdi:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rdi))
    old_rdi = rdi

    color(COLOR_REGNAME)
    output("  RSI: ")
    if rsi == old_rsi:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rsi))
    old_rsi = rsi

    color(COLOR_REGNAME)
    output("  RDX: ")
    if rdx == old_rdx:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rsp))
    old_rdx = rdx

    color(COLOR_REGNAME)
    output("  RCX: ")
    if rcx == old_rcx:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rcx))
    old_rcx = rcx

    color(COLOR_REGNAME)
    output("  RIP: ")
    if rip == old_rip:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (rip))
    old_rip = rip
    output("\n")

    color(COLOR_REGNAME)
    output("  R8:  ")
    if r8 == old_r8:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r8))
    old_r8 = r8

    color(COLOR_REGNAME)
    output("  R9:  ")
    if r9 == old_r9:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r9))
    old_r9 = r9

    color(COLOR_REGNAME)
    output("  R10: ")
    if r10 == old_r10:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r10))
    old_r10 = r10

    color(COLOR_REGNAME)
    output("  R11: ")
    if r11 == old_r11:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r11))
    old_r11 = r11

    color(COLOR_REGNAME)
    output("  R12: ")
    if r12 == old_r12:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r12))
    old_r12 = r12

    output("\n")

    color(COLOR_REGNAME)
    output("  R13: ")
    if r13 == old_r13:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r13))
    old_r13 = r13

    color(COLOR_REGNAME)
    output("  R14: ")
    if r14 == old_r14:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r14))
    old_r14 = r14

    color(COLOR_REGNAME)
    output("  R15: ")
    if r15 == old_r15:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.016lX" % (r15))
    old_r15 = r15
    output("\n")

    color(COLOR_REGNAME)
    output("  CS:  ")
    if cs == old_cs:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (cs))
    old_cs = cs

    color(COLOR_REGNAME)
    output("  FS: ")
    if fs == old_fs:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (fs))
    old_fs = fs

    color(COLOR_REGNAME)
    output("  GS: ")
    if gs == old_gs:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (gs))
    old_gs = gs
    output("\n")


def reg32():
    global old_eax
    global old_ecx
    global old_edx
    global old_ebx
    global old_esp
    global old_ebp
    global old_esi
    global old_edi
    global old_eflags
    global old_cs
    global old_ds
    global old_fs
    global old_gs
    global old_ss
    global old_es
    global old_eip

    color(COLOR_REGNAME)
    output("  EAX: ")
    eax = int(get_register("eax"), 16)
    if eax == old_eax:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (eax))
    old_eax = eax

    color(COLOR_REGNAME)
    output("  EBX: ")
    ebx = int(get_register("ebx"), 16)
    if ebx == old_ebx:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (ebx))
    old_ebx = ebx

    color(COLOR_REGNAME)
    output("  ECX: ")
    ecx = int(get_register("ecx"), 16)
    if ecx == old_ecx:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (ecx))
    old_ecx = ecx

    color(COLOR_REGNAME)
    output("  EDX: ")
    edx = int(get_register("edx"), 16)
    if edx == old_edx:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (edx))
    old_edx = edx

    output("  ")
    eflags = int(get_register("eflags"), 16)
    color_bold()
    color_underline()
    color(COLOR_CPUFLAGS)
    dump_eflags(eflags)
    color_reset()

    output("\n")

    color(COLOR_REGNAME)
    output("  ESI: ")
    esi = int(get_register("esi"), 16)
    if esi == old_esi:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (esi))
    old_esi = esi

    color(COLOR_REGNAME)
    output("  EDI: ")
    edi = int(get_register("edi"), 16)
    if edi == old_edi:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (edi))
    old_edi = edi

    color(COLOR_REGNAME)
    output("  EBP: ")
    ebp = int(get_register("ebp"), 16)
    if ebp == old_ebp:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (ebp))
    old_ebp = ebp

    color(COLOR_REGNAME)
    output("  ESP: ")
    esp = int(get_register("esp"), 16)
    if esp == old_esp:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (esp))
    old_esp = esp

    color(COLOR_REGNAME)
    output("  EIP: ")
    eip = int(get_register("eip"), 16)
    if eip == old_eip:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("0x%.08X" % (eip))
    old_eip = eip
    output("\n")

    color(COLOR_REGNAME)
    output("  CS:  ")
    cs = int(get_register("cs"), 16)
    if cs == old_cs:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (cs))
    old_cs = cs

    color(COLOR_REGNAME)
    output("  DS: ")
    ds = int(get_register("ds"), 16)
    if ds == old_ds:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (ds))
    old_ds = ds

    color(COLOR_REGNAME)
    output("  ES: ")
    es = int(get_register("es"), 16)
    if es == old_es:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (es))
    old_es = es

    color(COLOR_REGNAME)
    output("  FS: ")
    fs = int(get_register("fs"), 16)
    if fs == old_fs:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (fs))
    old_fs = fs

    color(COLOR_REGNAME)
    output("  GS: ")
    gs = int(get_register("gs"), 16)
    if gs == old_gs:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (gs))
    old_gs = gs

    color(COLOR_REGNAME)
    output("  SS: ")
    ss = int(get_register("ss"), 16)
    if ss == old_ss:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (ss))
    old_ss = ss
    output("\n")


def regARM32():
    global oldr0
    global oldr1
    global oldr2
    global oldr3
    global oldr4
    global oldr5
    global oldr6
    global oldr7
    global oldr8
    global oldr9
    global oldr10
    global oldr11
    global oldr12
    global oldsp
    global oldlr

    color(COLOR_REGNAME)
    output("  R0: ")
    r0 = int(get_register("r0"), 16)
    if r0 == oldr0:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r0))
    oldr0 = r0

    color(COLOR_REGNAME)
    output("  R1: ")
    r1 = int(get_register("r1"), 16)
    if r1 == oldr1:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r1))
    oldr1 = r1

    color(COLOR_REGNAME)
    output("  R2: ")
    r2 = int(get_register("r2"), 16)
    if r2 == oldr2:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r2))
    oldr2 = r2

    color(COLOR_REGNAME)
    output("  R3: ")
    r3 = int(get_register("r3"), 16)
    if r3 == oldr3:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r3))
    oldr3 = r3

    color(COLOR_REGNAME)
    output("  R4: ")
    r4 = int(get_register("r4"), 16)
    if r4 == oldr4:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r4))
    oldr4 = r4

    output("  ")
    output("\n")

    color(COLOR_REGNAME)
    output("  R5: ")
    r5 = int(get_register("r5"), 16)
    if r5 == oldr5:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r5))
    oldr5 = r5

    color(COLOR_REGNAME)
    output("  R6: ")
    r6 = int(get_register("r6"), 16)
    if r6 == oldr6:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r6))
    oldr6 = r6

    color(COLOR_REGNAME)
    output("  R7: ")
    r7 = int(get_register("r7"), 16)
    if r7 == oldr7:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r7))
    oldr7 = r7

    color(COLOR_REGNAME)
    output("  R8: ")
    r8 = int(get_register("r8"), 16)
    if r8 == oldr8:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r8))
    oldr8 = r8

    color(COLOR_REGNAME)
    output("  R9: ")
    r9 = int(get_register("r9"), 16)
    if r9 == oldr9:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r9))
    oldr9 = r9

    output("  ")
    output("\n")

    color(COLOR_REGNAME)
    output("  R10: ")
    r10 = int(get_register("r10"), 16)
    if r10 == oldr10:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r10))
    oldr10 = r10

    color(COLOR_REGNAME)
    output("  R11: ")
    r11 = int(get_register("r11"), 16)
    if r11 == oldr11:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r11))
    oldr11 = r11

    color(COLOR_REGNAME)
    output("  R12: ")
    r12 = int(get_register("r12"), 16)
    if r12 == oldr12:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (r12))
    oldr12 = r12

    color(COLOR_REGNAME)
    output("  SP: ")
    sp = int(get_register("sp"), 16)
    if sp == oldsp:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (sp))
    oldsp = sp

    color(COLOR_REGNAME)
    output("  LR: ")
    lr = int(get_register("lr"), 16)
    if lr == oldlr:
        color(COLOR_REGVAL)
    else:
        color(COLOR_REGVAL_MODIFIED)
    output("%.04X" % (lr))
    oldlr = lr


def print_registers():
    if is_i386():
        reg32()
    elif is_x64():
        reg64()
    elif is_arm32():
        regARM32()


def get_GPRs():
    """
    Returns the general purpose registers of the frame as an SBValue.

    The returned SBValue object is iterable.  An example:
        ...
        from lldbutil import get_GPRs
        regs = get_GPRs(frame)
        for reg in regs:
            print "%s => %s" % (reg.GetName(), reg.GetValue())
        ...
    """
    return get_registers("general purpose")


def HandleHookStopOnTarget(debugger, command, result, dict):
    global GlobalListOutput

    GlobalListOutput = []

    arch = get_arch()
    if not is_i386() and not is_x64() and not is_arm32():
        #this is for ARM64 probably in the future... when I will need it...
        print("Unknown architecture : " + arch)
        return

    output("\n")
    color(COLOR_SEPARATOR)
    if is_i386() or is_arm32():
        output("---------------------------------------------------------------------------------")
    elif is_x64():
        output("-----------------------------------------------------------------------------------------------------------------------")

    color_bold()
    output("[regs]\n")
    color_reset()
    print_registers()

    color(COLOR_SEPARATOR)
    if is_i386() or is_arm32():
            output("---------------------------------------------------------------------------------")
    elif is_x64():
            output("-----------------------------------------------------------------------------------------------------------------------")
    color_bold()
    output("[code]\n")
    color_reset()

    if is_i386():
        pc = get_register("eip")
    elif is_x64():
        pc = get_register("rip")

    #debugger.HandleCommand("disassemble --start-address=" + pc + " --count=8")
        res = lldb.SBCommandReturnObject()
        lldb.debugger.GetCommandInterpreter().HandleCommand("disassemble --start-address=" + pc + " --count=8", res)

    data = res.GetOutput()
    #split lines... and mark currently executed code...
    data = data.split("\n")
    for x in data:
        if x[0:2] == "->":
            color(COLOR_HIGHLIGHT_LINE)
            color_bold()
            output(x)
            color_reset()
        else:
            output(x)
        output("\n")
    #output(res.GetOutput())
    color(COLOR_SEPARATOR)
    if is_i386() or is_arm32():
            output("---------------------------------------------------------------------------------------")
    elif is_x64():
            output("-----------------------------------------------------------------------------------------------------------------------------")
    color_reset()
    output("\n")

    #stop reason is just a number, we need StopDescription...
    #output("Stop reason : " + str(lldb.debugger.GetSelectedTarget().process.selected_thread.GetStopReason()))
    #output("\n")
    output("Stop reason : " + str(lldb.debugger.GetSelectedTarget().process.selected_thread.GetStopDescription(100)))

    result.PutCString("".join(GlobalListOutput))
    result.SetStatus(lldb.eReturnStatusSuccessFinishResult)


def LoadBreakPoints(debugger, command, result, dict):
    global GlobalOutputList
    GlobalOutputList = []
    try:
        f = open(command, "r")
    except:
        output("Failed to load file : " + command)
        result.PutCString("".join(GlobalListOutput))
        return
    while True:
        line = f.readline()
        if not line:
            break
        line = line.rstrip()
        if not line:
            break
        debugger.HandleCommand("breakpoint set --name " + line)
    f.close()


def si(debugger, command, result, dict):
    '''
        si, c, r instruction override deault ones to consume their output.
        For example:
            si is thread step-in which by default dumps thread and frame info
            after every step. Consuming output of this instruction allows us
            to nicely display informations in our hook-stop
        Same goes for c and r (continue and run)
    '''
    res = lldb.SBCommandReturnObject()
    lldb.debugger.GetCommandInterpreter().HandleCommand("thread step-inst", res)
    return


def c(debugger, command, result, dict):
    res = lldb.SBCommandReturnObject()
    lldb.debugger.GetCommandInterpreter().HandleCommand("process continue", res)


def r(debugger, command, result, dict):
    res = lldb.SBCommandReturnObject()
    if command[0:3] == "-c/":
        index = command.find("--")
        command = command[index+2:]
    #strip -c/bin/sh or -c/bin/bash -- when arguments are passed to cmd line...
    lldb.debugger.GetCommandInterpreter().HandleCommand("process launch -- " + command, res)


def DumpInstructions(debugger, command, result, dict):
    '''
        Handles 'u' command which displays instructions. Also handles output of
        'disassemble' command ...
    '''
    global GlobalListOutput
    GlobalListOutput = []

    res = lldb.SBCommandReturnObject()
    cmd = command.split()
    handleCmd = lldb.debugger.GetCommandInterpreter().HandleCommand
    if len(cmd) == 0 or len(cmd) > 2:
        handleCmd("disassemble --start-address=$pc --count=8", res)
    elif len(cmd) == 1:
        handleCmd("disassemble --start-address=%s --count=8" % cmd[0], res)
    else:
        handleCmd("disassemble --start-address=%s --count=%s" % (cmd[0], cmd[1]), res)

    if res.Succeeded() is True:
        output(res.GetOutput())
    else:
        output("Error getting instructions for : " + command)

    result.PutCString("".join(GlobalListOutput))
    result.SetStatus(lldb.eReturnStatusSuccessFinishResult)


def stepo(debugger, command, result, dict):
    '''
        Implements stepover instruction. Unfortunatelly here is no internal breakpoint exposed to Python
        thus all breaks have to be visible. Internal breakpoints are breakpoints which are < 0 (eg. -1 etc...)
        and their existance is visible from :
        lldb/sources/Target/Target.cpp

        BreakpointSP
        Target::CreateBreakpoint (const FileSpecList *containingModules,
                                  const FileSpec &file,
                                  uint32_t line_no,
                                  LazyBool check_inlines,
                                  LazyBool skip_prologue,
                                  bool internal,
                                  bool hardware)

    '''
    global GlobalListOutput
    GlobalListOutput = []

    target = lldb.debugger.GetSelectedTarget()
    if is_i386():
            pc = lldb.SBAddress(int(get_register("eip"), 16), target)
    elif is_x64():
            pc = lldb.SBAddress(int(get_register("rip"), 16), target)

    inst = lldb.SBTarget.ReadInstructions(target, pc, 2, "intel")

    pc_inst = inst[0]
    pc_inst = str(pc_inst).split()[1]

    pc_inst = inst[0].GetMnemonic(target)
    if is_i386():
        pc = int(get_register("eip"), 16) + inst[0].GetByteSize()
    elif is_x64():
        pc = int(get_register("rip"), 16) + inst[0].GetByteSize()

    if "call" in pc_inst or "movs" in pc_inst or "stos" in pc_inst or "loop" in pc_inst or "cmps" in pc_inst:

        breakpoint = target.BreakpointCreateByAddress(pc)
        breakpoint.SetOneShot(True)
        debugger.HandleCommand("c")
    else:
        debugger.HandleCommand("si")


def hexdump(addr, chars, sep, width):
    l = []
    while chars:
        line = chars[:width]
        chars = chars[width:]
        line = line.ljust(width, '\000')
    if is_i386() or is_arm32():
        szaddr = "0x%.08X" % addr
    elif is_x64():
        szaddr = "0x%.016lX" % addr
    l.append("\033[1m%s :\033[0m %s%s \033[1m%s\033[0m" % (szaddr, sep.join("%02X" % ord(c) for c in line), sep, quotechars(line)))
    addr += 0x10
    return "\n".join(l)


def quotechars(chars):
    return ''.join(['.', c][c.isalnum()] for c in chars)


def dd(debugger, command, result, dict):
    '''
        Output nice hexdump... Should be db (in the future) so we can give dw/dd/dq
        outputs as it's done with any normal debugger...
    '''
    global GlobalListOutput

    GlobalListOutput = []

    value = get_frame().EvaluateExpression(command)
    if value.IsValid() is False:
            output("Error evaluating expression : " + command)
            result.PutCString("".join(GlobalListOutput))
            return
    try:
            value = int(value.GetValue(), 10)
    except:
            output("Error evaluating expression : " + command)
            result.PutCString("".join(GlobalListOutput))
            return

    err = lldb.SBError()
    target = lldb.debugger.GetSelectedTarget()
    membuff = target.GetProcess().ReadMemory(value, 0x100, err)
    if err.Success() is False:
            output(str(err))
            result.PutCString("".join(GlobalListOutput))
            return

    color(BLUE)
    if is_i386():
            output("[0x0000:0x%.08X]" % value)
            output("------------------------------------------------------")
    elif is_x64():
            output("[0x0000:0x%.016lX]" % value)
            output("------------------------------------------------------")
    color_bold()
    output("[data]")
    color_reset()
    output("\n")
    #output(hexdump(value, membuff, " ", 16))
    index = 0
    while index < 0x100:
        data = struct.unpack("B" * 16, membuff[index:index + 0x10])
        if is_i386() or is_arm32():
                szaddr = "0x%.08X" % value
        elif is_x64():
                szaddr = "0x%.016lX" % value
    fmtnice = "%.02X %.02X %.02X %.02X %.02X %.02X %.02X %.02X"
    fmtnice = fmtnice + " - " + fmtnice
    output("\033[1m%s :\033[0m %.02X %.02X %.02X %.02X %.02X %.02X %.02X %.02X - %.02X %.02X %.02X %.02X %.02X %.02X %.02X %.02X \033[1m%s\033[0m" % (
            szaddr,
            data[0],
            data[1],
            data[2],
            data[3],
            data[4],
            data[5],
            data[6],
            data[7],
            data[8],
            data[9],
            data[10],
            data[11],
            data[12],
            data[13],
            data[14],
            data[15],
            quotechars(membuff[index:index+0x10])))
    if index + 0x10 != 0x100:
        output("\n")
    index += 0x10
    value += 0x10
    color_reset()
    #last element of the list has all data output...
    #so we remove last \n
    result.PutCString("".join(GlobalListOutput))
    result.SetStatus(lldb.eReturnStatusSuccessFinishResult)


def dq(debugger, command, result, dict):
    global GlobalListOutput

    GlobalListOutput = []

    value = get_frame().EvaluateExpression(command)
    if value.IsValid() is False:
        output("Error evaluating expression : " + command)
        result.PutCString("".join(GlobalListOutput))
        return
    try:
        value = int(value.GetValue(), 10)
    except:
        output("Error evaluating expression : " + command)
        result.PutCString("".join(GlobalListOutput))
        return

    err = lldb.SBError()
    target = lldb.debugger.GetSelectedTarget()
    membuff = target.GetProcess().ReadMemory(value, 0x100, err)
    if err.Success() is False:
        output(str(err))
        result.PutCString("".join(GlobalListOutput))
        return

    color(BLUE)
    if is_i386():
            output("[0x0000:0x%.08X]" % value)
            output("-------------------------------------------------------")
    elif is_x64():
            output("[0x0000:0x%.016lX]" % value)
            output("-------------------------------------------------------")
    color_bold()
    output("[data]")
    color_reset()
    output("\n")
    index = 0
    while index < 0x100:
        (mem0, mem1, mem2, mem3) = struct.unpack("QQQQ", membuff[index:index + 0x20])
        if is_i386():
            szaddr = "0x%.08X" % value
        elif is_x64():
            szaddr = "0x%.016lX" % value
        output("\033[1m%s :\033[0m %.016lX %.016lX %.016lX %.016lX" % (szaddr, mem0, mem1, mem2, mem3))
        if index + 0x20 != 0x100:
            output("\n")
        index += 0x20
        value += 0x20
    color_reset()
    result.PutCString("".join(GlobalListOutput))
    result.SetStatus(lldb.eReturnStatusSuccessFinishResult)


def ddword(debugger, command, result, dict):
    global GlobalListOutput

    GlobalListOutput = []

    value = get_frame().EvaluateExpression(command)
    if value.IsValid() is False:
        output("Error evaluating expression : " + command)
        result.PutCString("".join(GlobalListOutput))
        return
    try:
        value = int(value.GetValue(), 10)
    except:
        output("Error evaluating expression : " + command)
        result.PutCString("".join(GlobalListOutput))
        return

    err = lldb.SBError()
    target = lldb.debugger.GetSelectedTarget()
    membuff = target.GetProcess().ReadMemory(value, 0x100, err)
    if err.Success() is False:
        output(str(err))
        result.PutCString("".join(GlobalListOutput))
        return

    color(BLUE)
    if is_i386():
            output("[0x0000:0x%.08X]" % value)
            output("----------------------------------------")
    elif is_x64():
            output("[0x0000:0x%.016lX]" % value)
            output("----------------------------------------")
    color_bold()
    output("[data]")
    color_reset()
    output("\n")
    index = 0
    while index < 0x100:
        (mem0, mem1, mem2, mem3) = struct.unpack("IIII", membuff[index:index + 0x10])
        if is_i386() or is_arm32():
            szaddr = "0x%.08X" % value
        elif is_x64():
            szaddr = "0x%.016lX" % value
        output("\033[1m%s :\033[0m %.08X %.08X %.08X %.08X \033[1m%s\033[0m" % (szaddr,
                                    mem0,
                                    mem1,
                                    mem2,
                                    mem3,
                                    quotechars(membuff[index:index + 0x10])))
        if index + 0x10 != 0x100:
                output("\n")
        index += 0x10
        value += 0x10
    color_reset()
    result.PutCString("".join(GlobalListOutput))
    result.SetStatus(lldb.eReturnStatusSuccessFinishResult)


def dw(debugger, command, result, dict):
    global GlobalListOutput

    GlobalListOutput = []

    value = get_frame().EvaluateExpression(command)
    if value.IsValid() is False:
        output("Error evaluating expression : " + command)
        result.PutCString("".join(GlobalListOutput))
        return
    try:
        value = int(value.GetValue(), 10)
    except:
        output("Error evaluating expression : " + command)
        result.PutCString("".join(GlobalListOutput))
        return

    err = lldb.SBError()
    target = lldb.debugger.GetSelectedTarget()
    membuff = target.GetProcess().ReadMemory(value, 0x100, err)
    if err.Success() is False:
        output(str(err))
        result.PutCString("".join(GlobalListOutput))
        return

    color(BLUE)
    if is_i386():
            output("[0x0000:0x%.08X]" % value)
            output("--------------------------------------------")
    elif is_x64():
            output("[0x0000:0x%.016lX]" % value)
            output("--------------------------------------------")
    color_bold()
    output("[data]")
    color_reset()
    output("\n")
    index = 0
    while index < 0x100:
        data = struct.unpack("HHHHHHHH", membuff[index:index + 0x10])
        if is_i386() or is_arm32():
            szaddr = "0x%.08X" % value
        elif is_x64():
            szaddr = "0x%.016lX" % value
        output("\033[1m%s :\033[0m %.04X %.04X %.04X %.04X %.04X %.04X %.04X %.04X \033[1m%s\033[0m" % (szaddr,
                data[0],
                data[1],
                data[2],
                data[3],
                data[4],
                data[5],
                data[6],
                data[7],
                quotechars(membuff[index:index + 0x10])))
        if index + 0x10 != 0x100:
                output("\n")
        index += 0x10
        value += 0x10
    color_reset()
    result.PutCString("".join(GlobalListOutput))
    result.SetStatus(lldb.eReturnStatusSuccessFinishResult)
