import { Pipe, PipeTransform } from '@angular/core';

import { Money } from '../models/api';

const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

/** "1299.00" (DRF decimal string) -> "$1,299.00". Display only: never do arithmetic on money in the client. */
@Pipe({ name: 'money' })
export class MoneyPipe implements PipeTransform {
  transform(value: Money | null | undefined): string {
    if (value === null || value === undefined || value === '') return '';
    const amount = Number(value);
    return Number.isFinite(amount) ? usd.format(amount) : value;
  }
}
