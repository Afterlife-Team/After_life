"""Try Wayback first, then an independent archive without retrying its cooldown."""
from services import archive_site as wayback, arquivo
from services.security import validate_public_url


def recover_from_url(url,year=None):
    url=validate_public_url(url)
    if year is not None and (type(year) is not int or not 1996 <= year <= 2100):
        raise wayback.ArchiveError('Invalid archive year.')
    failures=[]
    try:
        snapshot=wayback.find_snapshot(url,year)
        if snapshot:
            snapshot['requested_year']=year
            bundle=wayback.recover_archived_site(snapshot)
            bundle.recovery['capture']['provider']='Wayback Machine'
            return bundle
        failures.append('Wayback: no matching capture')
    except wayback.ArchiveError as exc:
        failures.append(f'Wayback: {exc}')
    try:
        snapshot=arquivo.find_snapshot(url,year)
        if snapshot:
            bundle=arquivo.recover(snapshot)
            bundle.warnings.insert(0,'Wayback was unavailable or had no usable capture; recovered from Arquivo.pt instead.')
            bundle.recovery['fallback']={'used':True,'primary':'Wayback Machine','reason':failures[0]}
            return bundle
        failures.append('Arquivo.pt: no matching capture for this URL/year')
    except wayback.ArchiveError as exc:
        failures.append(f'Arquivo.pt: {exc}')
    raise wayback.ArchiveError('No usable archived copy was recovered. ' + ' | '.join(failures))
