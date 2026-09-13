/**
 * @file    can_protocol.h
 * @brief   双板 CAN 通信协议 (F407 主控 <-> F103 驱动板)
 *
 * 速率 500kbps, 标准帧 11 位 ID, 总线两端 120Ω 终端电阻。
 *
 * 帧定义:
 *   0x100 指令帧 (主控 -> 驱动板): 目标速度/高度/跳跃/模式/急停
 *   0x200 状态帧 (驱动板 -> 主控): 姿态/轮速/位移/电量/故障标志
 *
 * 数据都用定点数 (×100) 打包, 避免浮点字节序问题, 便于调试。
 * 每帧 8 字节, 符合 CAN 经典帧最大数据长度。
 */

#ifndef CAN_PROTOCOL_H
#define CAN_PROTOCOL_H

#include <stdint.h>

/* ============ CAN ID ============ */
#define CAN_ID_COMMAND  0x100u   /* 主控 -> 驱动板 */
#define CAN_ID_STATUS   0x200u   /* 驱动板 -> 主控 */

/* ============ 指令帧 (0x100, 主控 -> 驱动) ============ */
typedef struct {
    int16_t linear_vel;   /* 目标线速度 (×100, 前进为正) */
    int16_t angular_vel;  /* 目标角速度 (×100, 左转为正) */
    uint8_t height;       /* 目标高度 (0~100%) */
    uint8_t mode;         /* 模式: 0=停止 1=平衡 2=跳跃 */
    uint8_t jump;         /* 跳跃触发: 0=无 1=触发一次 */
    uint8_t estop;        /* 急停: 0=正常 1=急停 */
} CanCommand;

/* ============ 状态帧 (0x200, 驱动 -> 主控) ============ */
typedef struct {
    int16_t pitch_angle;  /* 俯仰角 (×100, 度) */
    int16_t pitch_rate;   /* 俯仰角速度 (×100, 度/秒) */
    int16_t wheel_speed;  /* 轮部平均转速 (×100) */
    uint8_t battery;      /* 电池电压 (×10, 伏) */
    uint8_t flags;        /* 标志位: bit0=失控 bit1=轮离地 bit2=低电量 */
} CanStatus;

/* 状态帧 flags 位定义 */
#define STATUS_FLAG_UNCONTROLLED  (1u << 0)
#define STATUS_FLAG_AIRBORNE      (1u << 1)
#define STATUS_FLAG_LOW_BATTERY   (1u << 2)

/* ============ 编解码 (小端) ============ */

/** 把指令打包进 8 字节 CAN 数据 */
void can_encode_command(const CanCommand *cmd, uint8_t data[8]);

/** 从 8 字节 CAN 数据解出指令 */
void can_decode_command(const uint8_t data[8], CanCommand *cmd);

/** 把状态打包进 8 字节 CAN 数据 */
void can_encode_status(const CanStatus *st, uint8_t data[8]);

/** 从 8 字节 CAN 数据解出状态 */
void can_decode_status(const uint8_t data[8], CanStatus *st);

#endif /* CAN_PROTOCOL_H */
