/**
 * @file    main_control.c
 * @brief   主控板应用层实现
 *
 * 职责:
 *   1. CAN 主机: 向驱动板发指令(速度/高度/跳跃/急停), 收状态
 *   2. 腿部舵机: STS3032 高度控制 (同步写位置)
 *   3. 简单状态机: 停止 -> 平衡 -> 运动
 */

#include "main_control.h"
#include "stm32f4xx_hal.h"
#include "../hal/sts3032.h"
#include "../../common/can_protocol/can_protocol.h"

/* 舵机 ID: 左=1 右=2 (参考项目) */
#define SERVO_ID_LEFT   1
#define SERVO_ID_RIGHT  2
#define SERVO_CENTER    2048
#define SERVO_OFFSET    12

/* 高度 -> 舵机位置的映射 (参考: 8.4*(height-32)) */
#define HEIGHT_TO_POS(h)  (SERVO_CENTER + SERVO_OFFSET + (int16_t)(8.4f * (h - 32)))

static CanCommand  g_cmd;      /* 发给驱动板的指令 */
static CanStatus   g_status;   /* 收到的驱动板状态 */
static uint8_t     g_robot_go; /* 平衡使能 */

/* ---- 外部句柄 (main.c) ---- */
extern UART_HandleTypeDef huart6;  /* 舵机总线 */
extern CAN_HandleTypeDef hcan1;    /* 与驱动板通信 */

/* 发送同步写位置到两个舵机 */
static void servo_write_position(int16_t pos_left, int16_t pos_right,
                                 uint16_t speed, uint8_t acc)
{
    StsServoCmd cmds[2] = {
        {SERVO_ID_LEFT,  pos_left,  speed, acc},
        {SERVO_ID_RIGHT, pos_right, speed, acc},
    };
    uint8_t buf[64];
    int len = sts3032_build_sync_write(cmds, 2, buf);
    HAL_UART_Transmit(&huart6, buf, (uint16_t)len, 10);
}

/* 发送 CAN 指令帧到驱动板 */
static void can_send_command(const CanCommand *cmd)
{
    uint8_t data[8];
    uint32_t mailbox;
    CAN_TxHeaderTypeDef header;

    can_encode_command(cmd, data);
    header.StdId = CAN_ID_COMMAND;
    header.ExtId = 0;
    header.IDE = CAN_ID_STD;
    header.RTR = CAN_RTR_DATA;
    header.DLC = 8;
    header.TransmitGlobalTime = DISABLE;
    HAL_CAN_AddTxMessage(&hcan1, &header, data, &mailbox);
}

void main_control_init(void)
{
    g_robot_go = 0;
    g_cmd.linear_vel = 0;
    g_cmd.angular_vel = 0;
    g_cmd.height = 38;     /* 参考默认高度 */
    g_cmd.mode = 0;
    g_cmd.jump = 0;
    g_cmd.estop = 1;       /* 初始急停 */

    /* 腿部初始蹲下位置 (参考 Position[0]=2148, Position[1]=1948) */
    servo_write_position(2148, 1948, 300, 30);
}

void main_control_loop(void)
{
    /* 状态机: 简单示例, 后续接网页/按键控制 */
    static uint32_t tick = 0;
    tick++;

    /* 每 10ms 发一次指令帧 */
    if (tick % 10 == 0) {
        if (g_robot_go) {
            g_cmd.estop = 0;
            g_cmd.height = 38;  /* 站立高度 */
        }
        can_send_command(&g_cmd);
    }

    /* 腿部高度控制 (跟随 g_cmd.height) */
    {
        int16_t pos_l = HEIGHT_TO_POS(g_cmd.height);
        int16_t pos_r = 2 * SERVO_CENTER - pos_l;  /* 右腿镜像 */
        if (g_cmd.height >= 32) {
            servo_write_position(pos_l, pos_r, 200, 8);
        }
    }
}

void main_control_on_can_rx(const uint8_t data[8])
{
    can_decode_status(data, &g_status);
    /* 若驱动板报失控, 这里可做安全处理 */
    if (g_status.flags & STATUS_FLAG_UNCONTROLLED) {
        g_robot_go = 0;
        g_cmd.estop = 1;
    }
}
