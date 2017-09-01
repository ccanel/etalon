--- linux-3.16.3-clean/include/uapi/asm-generic/unistd.h	2014-09-17 11:22:16.000000000 -0600
+++ ./linux-3.16.3-vtmininet/include/uapi/asm-generic/unistd.h	2017-08-29 10:02:36.892974290 -0600
@@ -700,8 +700,20 @@ __SYSCALL(__NR_sched_getattr, sys_sched_
 #define __NR_renameat2 276
 __SYSCALL(__NR_renameat2, sys_renameat2)
 
+/* virtual time system calls --- Jiaqi */
+// #define __NR_timeclone 277
+// __SYSCALL(__NR_timeclone, sys_timeclone)
+#define __NR_virtualtimeunshare 278
+__SYSCALL(__NR_virtualtimeunshare, sys_virtualtimeunshare)
+#define __NR_getvirtualtimeofday 279
+__SYSCALL(__NR_getvirtualtimeofday, sys_getvirtualtimeofday)
+#define __NR_helloworld 280
+__SYSCALL(__NR_helloworld, sys_helloworld)
+#define __NR_settimedilationfactor 281
+__SYSCALL(__NR_settimedilationfactor, sys_settimedilationfactor)
+
 #undef __NR_syscalls
-#define __NR_syscalls 277
+#define __NR_syscalls 281
 
 /*
  * All syscalls below here should go away really,
