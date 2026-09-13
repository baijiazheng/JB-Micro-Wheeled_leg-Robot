/**
 * @file    control_loop.h
 * @brief   1kHz 控制环: 编码器 + 平衡 + FOC -> PWM (把各模块串起来)
 *
 * 数据流:
 *   AS5600(角度) --FocControl 解绕/速度估计--> 电角度 + 转速
 *   MPU6050(姿态) ---------------------------> 俯仰角 + 角速度
 *   BalanceController(LQR) ------------------> 平衡转矩 U
 *   FOC 电压步(inverse_park+svpwm) -----------> 三相占空比
 *   PWM(L6234) -------------------------------> 电机
 */

#ifndef CONTROL_LOOP_H
#define CONTROL_LOOP_H

#include <stdint.h>

/** 初始化控制环 (绑定 I2C/CAN 句柄) */
void control_loop_init(void);

/** 1kHz 控制循环 (在定时器中断或主循环里每 1ms 调用一次) */
void control_loop_1khz(void);

/** 主循环后台任务 (CAN 接收处理等) */
void control_loop_background(void);

/** CAN 收到指令帧时由中断回调调用 */
void control_loop_on_can_rx(const uint8_t data[8]);

#endif /* CONTROL_LOOP_H */
