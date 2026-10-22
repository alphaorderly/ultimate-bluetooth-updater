/* Original 1.11, ARMv6-M / Thumb. No new persistent RAM.
 * r0: physical button snapshot from 0x01021848, before profile remapping.
 * Return original cycle result if no back button; otherwise zero.
 */
.syntax unified
.cpu cortex-m0
.thumb
.section .patch,"ax",%progbits
.global remap_entry
.type remap_entry,%function
.thumb_func
remap_entry:
    push {r4-r7,lr}
    sub sp,#4                  /* Preserve 8-byte alignment at every call. */
    mov r4,r0
    lsrs r5,r0,#25
    movs r1,#3
    ands r5,r1
    bne .Lback
    bl stock_cycle
    b .Lreturn
.Lback:
    bl stock_edge              /* Consume even a rejected two-back press. */
    cmp r5,#3
    beq .Ldone
    cmp r0,#0
    beq .Ldone
    lsls r4,r4,#14             /* Only physical bits 0..17 are targets. */
    lsrs r4,r4,#14
    ldr r7,=0x00020134
    ldrb r0,[r7]
    cmp r0,#3
    bcc .Lselected
    movs r0,#0
    strb r0,[r7]
    ldr r1,=0x000216de
    strh r0,[r1]               /* Stock profile view's selection mirror. */
    bl stock_macro_clear       /* Match stock switching out of off state. */
    movs r0,#0
.Lselected:
    lsls r1,r0,#2
    ldr r2,=0x000216cc
    ldr r3,=0x20200911
    str r3,[r2,r1]
    movs r1,#84
    muls r0,r1
    ldr r6,=0x000217ac
    adds r6,r6,r0
    ldr r0,[r6]
    cmp r0,r3
    beq .Lmap_ready
    str r3,[r6]
    adr r0,identity_bits
    movs r1,#0
    adds r2,r6,#4
.Lidentity:
    ldrb r3,[r0,r1]
    movs r7,#1
    lsls r7,r7,r3
    stmia r2!,{r7}
    adds r1,#1
    cmp r1,#18
    bne .Lidentity
    movs r0,#0
    str r0,[r6,#0x4c]
    str r0,[r6,#0x50]
.Lmap_ready:
    lsls r5,r5,#2              /* back25=1 -> +0x4c; back26=2 -> +0x50 */
    adds r5,#0x48
    str r4,[r6,r5]
    bl stock_macro_rebuild
    bl stock_overrides_clear
    ldr r0,=0x00020135
    movs r1,#1
    strb r1,[r0]
    bl stock_profile_flush
    bl stock_selection_validate
    bl stock_selection_flush  /* Detect and persist a changed mode selection. */
    bl pulse
    cmp r4,#0
    bne .Ldone
    movs r0,#60
    ldr r1,=pulse_gap
    bl stock_rumble_timer      /* Replace stop callback with stop + gap. */
.Ldone:
    movs r0,#0
.Lreturn:
    add sp,#4
    pop {r4-r7,pc}
.size remap_entry,.-remap_entry

.global pulse
.type pulse,%function
.thumb_func
pulse:
    push {r4,lr}
    movs r0,#60
    movs r1,#128
    movs r2,#128
    bl stock_rumble
    pop {r4,pc}
.size pulse,.-pulse

.global pulse_gap
.type pulse_gap,%function
.thumb_func
pulse_gap:
    push {r4,lr}
    bl stock_rumble_off
    movs r0,#70
    ldr r1,=pulse
    bl stock_rumble_timer
    pop {r4,pc}
.size pulse_gap,.-pulse_gap

.balign 4
identity_bits:
    .byte 13,12,4,5,10,11,14,15,1,2,3,0,16,17,9,8,7,6
.balign 4
.ltorg

.thumb_set stock_cycle,0x01027245
.thumb_set stock_edge,0x01023915
.thumb_set stock_macro_clear,0x01025e91
.thumb_set stock_macro_rebuild,0x01023739
.thumb_set stock_overrides_clear,0x010285e9
.thumb_set stock_profile_flush,0x010267e5
.thumb_set stock_selection_validate,0x0102a255
.thumb_set stock_selection_flush,0x0102c269
.thumb_set stock_rumble,0x0101c1d5
.thumb_set stock_rumble_timer,0x010265c1
.thumb_set stock_rumble_off,0x0102aa6b
.section .note.GNU-stack,"",%progbits
