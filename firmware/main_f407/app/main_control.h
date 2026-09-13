/**
 * @file    main_control.h
 * @brief   主控板应用层: CAN 主机 + 腿部舵机控制 + 状态机
 */

#ifndef MAIN_CONTROL_H
#define MAIN_CONTROL_H

#include <stdint.h>

/** 初始化 (绑定 UART/CAN 句柄) */
void main_control_init(void);

/** 后台循环 (周期调用): 发 CAN 指令 + 收状态 + 腿控制 */
void main_control_loop(void);

/** CAN 收到状态帧时由中断回调调用 */
void main_control_on_can_rx(const uint8_t data[8]);

#endif /* MAIN_CONTROL_H */
