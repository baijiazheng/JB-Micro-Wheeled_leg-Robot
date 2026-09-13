/**
 * @file    can_protocol.c
 * @brief   CAN 协议编解码实现 (小端)
 *
 * 手写字节打包(不用 memcpy), 保证字节序明确、跨平台一致,
 * 也便于调试时直接看原始字节。
 */

#include "can_protocol.h"

/* ============ 指令帧 ============ */
void can_encode_command(const CanCommand *cmd, uint8_t data[8])
{
    data[0] = (uint8_t)(cmd->linear_vel & 0xFF);
    data[1] = (uint8_t)((cmd->linear_vel >> 8) & 0xFF);
    data[2] = (uint8_t)(cmd->angular_vel & 0xFF);
    data[3] = (uint8_t)((cmd->angular_vel >> 8) & 0xFF);
    data[4] = cmd->height;
    data[5] = cmd->mode;
    data[6] = cmd->jump;
    data[7] = cmd->estop;
}

void can_decode_command(const uint8_t data[8], CanCommand *cmd)
{
    cmd->linear_vel  = (int16_t)((uint16_t)data[0] | ((uint16_t)data[1] << 8));
    cmd->angular_vel = (int16_t)((uint16_t)data[2] | ((uint16_t)data[3] << 8));
    cmd->height = data[4];
    cmd->mode   = data[5];
    cmd->jump   = data[6];
    cmd->estop  = data[7];
}

/* ============ 状态帧 ============ */
void can_encode_status(const CanStatus *st, uint8_t data[8])
{
    data[0] = (uint8_t)(st->pitch_angle & 0xFF);
    data[1] = (uint8_t)((st->pitch_angle >> 8) & 0xFF);
    data[2] = (uint8_t)(st->pitch_rate & 0xFF);
    data[3] = (uint8_t)((st->pitch_rate >> 8) & 0xFF);
    data[4] = (uint8_t)(st->wheel_speed & 0xFF);
    data[5] = (uint8_t)((st->wheel_speed >> 8) & 0xFF);
    data[6] = st->battery;
    data[7] = st->flags;
}

void can_decode_status(const uint8_t data[8], CanStatus *st)
{
    st->pitch_angle = (int16_t)((uint16_t)data[0] | ((uint16_t)data[1] << 8));
    st->pitch_rate  = (int16_t)((uint16_t)data[2] | ((uint16_t)data[3] << 8));
    st->wheel_speed = (int16_t)((uint16_t)data[4] | ((uint16_t)data[5] << 8));
    st->battery = data[6];
    st->flags   = data[7];
}
