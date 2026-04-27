"""Seed development data: admin user + sample PTO registry items."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory, engine
from app.db.base import Base
import app.db.models  # noqa: F401

REGISTRY_ITEMS = [
    ("КИ-001", "Кирпич керамический рядовой полнотелый М150 250×120×65 ГОСТ 530-2012", "шт", "Кирпич"),
    ("КИ-002", "Кирпич керамический рядовой пустотелый М125 250×120×65 ГОСТ 530-2012", "шт", "Кирпич"),
    ("КИ-003", "Кирпич силикатный рядовой М150 250×120×65 ГОСТ 379-2015", "шт", "Кирпич"),
    ("БЛ-001", "Блок газобетонный D500 600×300×200 ГОСТ 31360-2007", "шт", "Блоки"),
    ("БЛ-002", "Блок газобетонный D400 625×250×250 ГОСТ 31360-2007", "шт", "Блоки"),
    ("БЛ-003", "Блок пенобетонный D600 600×300×200 ГОСТ 25485-89", "шт", "Блоки"),
    ("БЛ-004", "Блок керамзитобетонный 390×190×188 ГОСТ 6133-2019", "шт", "Блоки"),
    ("АР-001", "Арматура А400 (АIII) ф8 ГОСТ 5781-82", "т", "Арматура"),
    ("АР-002", "Арматура А400 (АIII) ф10 ГОСТ 5781-82", "т", "Арматура"),
    ("АР-003", "Арматура А400 (АIII) ф12 ГОСТ 5781-82", "т", "Арматура"),
    ("АР-004", "Арматура А400 (АIII) ф14 ГОСТ 5781-82", "т", "Арматура"),
    ("АР-005", "Арматура А400 (АIII) ф16 ГОСТ 5781-82", "т", "Арматура"),
    ("АР-006", "Арматура А400 (АIII) ф20 ГОСТ 5781-82", "т", "Арматура"),
    ("АР-007", "Арматура А500С ф12 ГОСТ Р 52544-2006", "т", "Арматура"),
    ("АР-008", "Арматура А500С ф16 ГОСТ Р 52544-2006", "т", "Арматура"),
    ("БЕ-001", "Бетон тяжёлый В15 (М200) ГОСТ 26633-2015", "м³", "Бетон"),
    ("БЕ-002", "Бетон тяжёлый В20 (М250) ГОСТ 26633-2015", "м³", "Бетон"),
    ("БЕ-003", "Бетон тяжёлый В25 (М350) ГОСТ 26633-2015", "м³", "Бетон"),
    ("БЕ-004", "Бетон тяжёлый В30 (М400) ГОСТ 26633-2015", "м³", "Бетон"),
    ("БЕ-005", "Бетон тяжёлый В35 (М450) ГОСТ 26633-2015", "м³", "Бетон"),
    ("ЦМ-001", "Цемент ПЦ400 Д0 ГОСТ 31108-2020", "т", "Цемент"),
    ("ЦМ-002", "Цемент ПЦ500 Д0 ГОСТ 31108-2020", "т", "Цемент"),
    ("ЦМ-003", "Цемент ЦЕМ I 42.5Н ГОСТ 31108-2020", "т", "Цемент"),
    ("ПС-001", "Плита перекрытия ПК 60.15-8 ГОСТ 9561-2016", "шт", "Плиты перекрытий"),
    ("ПС-002", "Плита перекрытия ПБ 60-15-8 ГОСТ 26434-2015", "шт", "Плиты перекрытий"),
    ("ПС-003", "Плита перекрытия ПК 42.12-6 ГОСТ 9561-2016", "шт", "Плиты перекрытий"),
    ("МТ-001", "Металлочерепица МП Монтеррей 0.5мм ГОСТ Р 58153-2018", "м²", "Кровля"),
    ("МТ-002", "Профлист НС35 0.7мм ГОСТ 24045-2016", "м²", "Кровля"),
    ("УТ-001", "Утеплитель ROCKWOOL ЛАЙТ БАТТС 50мм ГОСТ 31189-2015", "м²", "Утеплитель"),
    ("УТ-002", "Утеплитель ROCKWOOL ЛАЙТ БАТТС 100мм ГОСТ 31189-2015", "м²", "Утеплитель"),
    ("УТ-003", "Пенополистирол ПСБ-С-25 50мм ГОСТ 15588-2014", "м²", "Утеплитель"),
    ("УТ-004", "Пенополистирол ЭППС 30мм Пеноплэкс 35 ГОСТ 32310-2012", "м²", "Утеплитель"),
    ("ГД-001", "Гипсокартон ГКЛ 12.5мм 1200×2500 ГОСТ 6266-97", "м²", "Гипсокартон"),
    ("ГД-002", "Гипсокартон ГКЛВ 12.5мм влагостойкий ГОСТ 6266-97", "м²", "Гипсокартон"),
    ("ТР-001", "Труба стальная электросварная ф57×3.5 ГОСТ 10704-91", "м.п.", "Трубы"),
    ("ТР-002", "Труба стальная водогазопроводная ДУ25 ГОСТ 3262-75", "м.п.", "Трубы"),
    ("ТР-003", "Труба ПВХ для канализации ф110 ГОСТ Р 51613-2000", "м.п.", "Трубы"),
    ("ТР-004", "Труба ПВХ для канализации ф50 ГОСТ Р 51613-2000", "м.п.", "Трубы"),
    ("ЛС-001", "Лестничный марш ЛМ 33.12.17-4 ГОСТ 9818-2015", "шт", "Лестничные элементы"),
    ("ЛС-002", "Лестничная площадка ЛП 30.12-4 ГОСТ 9818-2015", "шт", "Лестничные элементы"),
    ("ФУ-001", "Фундаментный блок ФБС 24.5.6-Т ГОСТ 13579-78", "шт", "Фундаменты"),
    ("ФУ-002", "Фундаментный блок ФБС 12.5.6-Т ГОСТ 13579-78", "шт", "Фундаменты"),
    ("СТ-001", "Стекло листовое М4 4мм ГОСТ 111-2014", "м²", "Стекло"),
    ("СТ-002", "Стеклопакет однокамерный 4-16-4 ГОСТ Р 54175-2010", "м²", "Стекло"),
    ("КР-001", "Краска фасадная силиконовая Caparol белая ГОСТ Р 52020-2003", "л", "Краски"),
    ("КР-002", "Грунтовка глубокого проникновения Ceresit CT 17 ГОСТ 28196-89", "л", "Краски"),
    ("ШТ-001", "Штукатурка цементная КНАУФ Ротбанд 30кг ГОСТ Р 56387-2015", "мешок", "Штукатурки"),
    ("ШТ-002", "Штукатурка гипсовая КНАУФ Ротбанд 25кг ГОСТ Р 56387-2015", "мешок", "Штукатурки"),
    ("КЛ-001", "Клей для плитки Ceresit CM 11 25кг ГОСТ Р 56387-2015", "мешок", "Клеи"),
    ("КЛ-002", "Клей для газобетона КНАУФ Поренбетон 25кг ГОСТ Р 55336-2012", "мешок", "Клеи"),
]


async def seed() -> None:
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Ensure extensions and schemas exist
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS control"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS pto"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS ntd"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS audit"))
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionFactory() as db:
        from app.modules.auth.models import User
        from app.modules.pto.models import RegistryItem
        from sqlalchemy import select

        # Create admin user if not exists
        existing = await db.execute(select(User).where(User.email == "admin@rezeb.ru"))
        if not existing.scalar_one_or_none():
            from app.modules.auth.models import UserRole
            admin = User(
                email="admin@rezeb.ru",
                hashed_password=hash_password("Admin123!"),
                full_name="Администратор",
                role=UserRole.superadmin,
                is_verified=True,
            )
            db.add(admin)
            print("Created admin user: admin@rezeb.ru / Admin123!")

        # Seed registry items
        count_result = await db.execute(select(RegistryItem))
        existing_count = len(count_result.scalars().all())
        if existing_count == 0:
            for code, name, unit, category in REGISTRY_ITEMS:
                item = RegistryItem(
                    code=code,
                    name=name,
                    name_normalized=name.lower(),
                    unit=unit,
                    category=category,
                )
                db.add(item)
            print(f"Seeded {len(REGISTRY_ITEMS)} registry items")
        else:
            print(f"Registry already has {existing_count} items, skipping seed")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
