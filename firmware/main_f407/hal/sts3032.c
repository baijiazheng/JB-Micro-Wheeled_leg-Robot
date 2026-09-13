/**
 * @file    sts3032.c
 * @brief   STS3032 同步写封包实现 (纯逻辑, 可 PC 测试)
 *
 * 参考飞特 SCServo 协议 + 原项目 Servo_STS3032.cpp。
 */

#include "sts3032.h"

#define INST_SYNC_WRITE  0x83u
#define MEM_ADDR_ACC     41u     /* SMS_STS_ACC */
#define DATA_LEN         7u      /* ACC + pos(2) + time(2) + speed(2) */

int sts3032_build_sync_write(const StsServoCmd *cmds, int n, uint8_t *buf)
{
    uint8_t mes_len = (uint8_t)((DATA_LEN + 1) * n + 4);
    uint8_t sum = 0;
    int idx = 0;

    /* 帧头 */
    buf[idx++] = 0xFF;
    buf[idx++] = 0xFF;
    buf[idx++] = 0xFE;          /* 广播 ID */
    buf[idx++] = mes_len;
    buf[idx++] = INST_SYNC_WRITE;
    buf[idx++] = MEM_ADDR_ACC;
    buf[idx++] = DATA_LEN;

    sum = (uint8_t)(0xFE + mes_len + INST_SYNC_WRITE + MEM_ADDR_ACC + DATA_LEN);

    /* 每个舵机: ID + 7 字节数据 */
    for (int i = 0; i < n; i++) {
        /* 位置: 负数 -> 取绝对值 + bit15 符号 */
        uint16_t pos = (uint16_t)cmds[i].position;
        if (cmds[i].position < 0) {
            pos = (uint16_t)(-cmds[i].position) | 0x8000u;
        }

        uint8_t data[7];
        data[0] = cmds[i].acc;
        data[1] = (uint8_t)(pos & 0xFF);        /* 位置低字节 */
        data[2] = (uint8_t)((pos >> 8) & 0xFF); /* 位置高字节 */
        data[3] = 0;                            /* 时间低字节 (未用) */
        data[4] = 0;                            /* 时间高字节 (未用) */
        data[5] = (uint8_t)(cmds[i].speed & 0xFF);        /* 速度低字节 */
        data[6] = (uint8_t)((cmds[i].speed >> 8) & 0xFF); /* 速度高字节 */

        buf[idx++] = cmds[i].id;
        sum = (uint8_t)(sum + cmds[i].id);
        for (int j = 0; j < 7; j++) {
            buf[idx++] = data[j];
            sum = (uint8_t)(sum + data[j]);
        }
    }

    /* 校验和: 取反 */
    buf[idx++] = (uint8_t)(~sum);

    return idx;
}
